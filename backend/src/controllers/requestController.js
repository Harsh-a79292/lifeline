const mongoose = require("mongoose");
const BloodRequest = require("../models/BloodRequest");
const User = require("../models/User");

const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];
const URGENCY_LEVELS = ["normal", "urgent", "critical"];

// ─── CREATE BLOOD REQUEST (Patient only) ─────────────────────────────────────
exports.createRequest = async (req, res) => {
  try {
    if (req.user.role !== "patient") {
      return res.status(403).json({ success: false, message: "Only patients can create blood requests" });
    }

    const { bloodGroup, units, hospitalName, city, contactPhone, urgency } = req.body;

    if (!bloodGroup || !units || !hospitalName || !city || !contactPhone) {
      return res.status(400).json({ success: false, message: "Please fill all required fields" });
    }
    if (!BLOOD_GROUPS.includes(bloodGroup)) {
      return res.status(400).json({ success: false, message: "Invalid blood group" });
    }
    if (!Number.isInteger(Number(units)) || Number(units) < 1 || Number(units) > 10) {
      return res.status(400).json({ success: false, message: "Units must be between 1 and 10" });
    }
    if (urgency && !URGENCY_LEVELS.includes(urgency)) {
      return res.status(400).json({ success: false, message: "Invalid urgency level" });
    }

    const request = await BloodRequest.create({
      patient: req.user.id,
      bloodGroup,
      units: Number(units),
      hospitalName: hospitalName.trim(),
      city: city.trim(),
      contactPhone: contactPhone.trim(),
      urgency: urgency || "normal",
    });

    // Emit socket notification to donors in that city — no phone included
    const io = req.app.get("io");
    if (io) {
      io.to(`donors-${city.trim().toLowerCase()}`).emit("new-blood-request", {
        requestId: request._id,
        bloodGroup: request.bloodGroup,
        units: request.units,
        hospitalName: request.hospitalName,
        city: request.city,
        urgency: request.urgency,
      });
    }

    return res.status(201).json({
      success: true,
      message: "Blood request created successfully",
      request: {
        _id: request._id,
        bloodGroup: request.bloodGroup,
        units: request.units,
        hospitalName: request.hospitalName,
        city: request.city,
        urgency: request.urgency,
        status: request.status,
        createdAt: request.createdAt,
      },
    });
  } catch (error) {
    console.error("Create request error:", error.message);
    if (error.name === "ValidationError") {
      return res.status(400).json({ success: false, message: "Invalid request data provided" });
    }
    return res.status(500).json({ success: false, message: "Failed to create blood request. Please try again later." });
  }
};

// ─── GET PENDING REQUESTS (Donor only — NEVER expose contactPhone) ────────────
exports.getRequests = async (req, res) => {
  try {
    if (req.user.role !== "donor") {
      return res.status(403).json({ success: false, message: "Only donors can view available requests" });
    }

    const requests = await BloodRequest.find({ status: "pending" })
      .select("bloodGroup units hospitalName city urgency status createdAt")
      .sort({ createdAt: -1 })
      .lean();

    return res.json({ success: true, count: requests.length, requests });
  } catch (error) {
    console.error("Get requests error:", error.message);
    return res.status(500).json({ success: false, message: "Failed to retrieve blood requests. Please try again later." });
  }
};

// ─── ACCEPT REQUEST (Donor only — atomic) ────────────────────────────────────
exports.acceptRequest = async (req, res) => {
  try {
    if (req.user.role !== "donor") {
      return res.status(403).json({ success: false, message: "Only donors can accept blood requests" });
    }
    if (!mongoose.Types.ObjectId.isValid(req.params.id)) {
      return res.status(400).json({ success: false, message: "Invalid request ID format" });
    }

    const request = await BloodRequest.findOneAndUpdate(
      { _id: req.params.id, status: "pending" },
      { $set: { status: "accepted", acceptedBy: req.user.id } },
      { new: true, runValidators: true }
    );

    if (!request) {
      return res.status(404).json({ success: false, message: "Request not found or already accepted" });
    }

    const io = req.app.get("io");
    if (io) {
      io.emit("request-accepted", { requestId: request._id, status: "accepted" });
    }

    // Return safe fields — contactPhone deliberately omitted from donor response
    return res.json({
      success: true,
      message: "Blood request accepted successfully",
      request: {
        _id: request._id,
        bloodGroup: request.bloodGroup,
        units: request.units,
        hospitalName: request.hospitalName,
        city: request.city,
        urgency: request.urgency,
        status: request.status,
        createdAt: request.createdAt,
      },
    });
  } catch (error) {
    console.error("Accept request error:", error.message);
    return res.status(500).json({ success: false, message: "Failed to accept blood request. Please try again later." });
  }
};

// ─── GET MY REQUESTS (Patient only — with populated donor name when accepted) ─
exports.getMyRequests = async (req, res) => {
  try {
    if (req.user.role !== "patient") {
      return res.status(403).json({ success: false, message: "Only patients can view their requests" });
    }

    const requests = await BloodRequest.find({ patient: req.user.id })
      .sort({ createdAt: -1 })
      .populate("acceptedBy", "name bloodGroup city") // safe fields only — no phone/email
      .lean();

    // Shape response — keep contactPhone since this is the patient's OWN request
    const shaped = requests.map((r) => ({
      _id: r._id,
      bloodGroup: r.bloodGroup,
      units: r.units,
      hospitalName: r.hospitalName,
      city: r.city,
      contactPhone: r.contactPhone,
      urgency: r.urgency,
      status: r.status,
      createdAt: r.createdAt,
      acceptedDonor: r.acceptedBy
        ? { name: r.acceptedBy.name, bloodGroup: r.acceptedBy.bloodGroup, city: r.acceptedBy.city }
        : null,
    }));

    return res.json({ success: true, count: shaped.length, requests: shaped });
  } catch (error) {
    console.error("Get my requests error:", error.message);
    return res.status(500).json({ success: false, message: "Failed to retrieve your blood requests. Please try again later." });
  }
};

// ─── GET DONOR'S ACCEPTED REQUESTS (Donor only) ───────────────────────────────
exports.getMyAccepted = async (req, res) => {
  try {
    if (req.user.role !== "donor") {
      return res.status(403).json({ success: false, message: "Only donors can view their accepted requests" });
    }

    const requests = await BloodRequest.find({
      acceptedBy: req.user.id,
      status: { $in: ["accepted", "fulfilled"] },
    })
      .sort({ createdAt: -1 })
      .lean();

    // For the donor's own accepted list, we share the hospital & city but NOT the patient phone
    const shaped = requests.map((r) => ({
      _id: r._id,
      bloodGroup: r.bloodGroup,
      units: r.units,
      hospitalName: r.hospitalName,
      city: r.city,
      urgency: r.urgency,
      status: r.status,
      createdAt: r.createdAt,
    }));

    return res.json({ success: true, count: shaped.length, requests: shaped });
  } catch (error) {
    console.error("Get my accepted error:", error.message);
    return res.status(500).json({ success: false, message: "Failed to retrieve accepted requests. Please try again later." });
  }
};

// ─── FULFIL REQUEST (Donor who accepted it only) ─────────────────────────────
exports.fulfillRequest = async (req, res) => {
  try {
    if (req.user.role !== "donor") {
      return res.status(403).json({ success: false, message: "Only donors can mark requests as fulfilled" });
    }
    if (!mongoose.Types.ObjectId.isValid(req.params.id)) {
      return res.status(400).json({ success: false, message: "Invalid request ID format" });
    }

    const request = await BloodRequest.findOneAndUpdate(
      { _id: req.params.id, acceptedBy: req.user.id, status: "accepted" },
      { $set: { status: "fulfilled" } },
      { new: true }
    );

    if (!request) {
      return res.status(404).json({ success: false, message: "Request not found, not accepted by you, or not in accepted state" });
    }

    return res.json({
      success: true,
      message: "Blood request marked as fulfilled",
      request: { _id: request._id, status: request.status },
    });
  } catch (error) {
    console.error("Fulfill request error:", error.message);
    return res.status(500).json({ success: false, message: "Failed to fulfil request. Please try again later." });
  }
};

// ─── CANCEL REQUEST (Patient who owns it, only if pending/accepted) ───────────
exports.cancelRequest = async (req, res) => {
  try {
    if (req.user.role !== "patient") {
      return res.status(403).json({ success: false, message: "Only patients can cancel blood requests" });
    }
    if (!mongoose.Types.ObjectId.isValid(req.params.id)) {
      return res.status(400).json({ success: false, message: "Invalid request ID format" });
    }

    const request = await BloodRequest.findOne({ _id: req.params.id });

    if (!request) {
      return res.status(404).json({ success: false, message: "Request not found" });
    }

    // Ownership check
    if (request.patient.toString() !== req.user.id) {
      return res.status(403).json({ success: false, message: "You can only cancel your own requests" });
    }

    // Status check — cannot cancel fulfilled or already cancelled
    if (!["pending", "accepted"].includes(request.status)) {
      return res.status(400).json({ success: false, message: `Cannot cancel a request with status '${request.status}'` });
    }

    request.status = "cancelled";
    await request.save();

    return res.json({
      success: true,
      message: "Blood request cancelled successfully",
      request: { _id: request._id, status: request.status },
    });
  } catch (error) {
    console.error("Cancel request error:", error.message);
    return res.status(500).json({ success: false, message: "Failed to cancel request. Please try again later." });
  }
};
