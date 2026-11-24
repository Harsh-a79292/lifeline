const express = require("express");
const router = express.Router();

const {
  createRequest,
  getRequests,
  getMyRequests,
  getMyAccepted,
  acceptRequest,
  fulfillRequest,
  cancelRequest,
} = require("../controllers/requestController");

const { protect } = require("../middleware/authMiddleware");

// Patient: create request
router.post("/", protect, createRequest);

// Patient: view own requests (with populated donor info)
router.get("/my", protect, getMyRequests);

// Patient: cancel own request
router.patch("/:id/cancel", protect, cancelRequest);

// Donor: view all pending requests (no phone)
router.get("/", protect, getRequests);

// Donor: view own accepted/fulfilled requests
router.get("/my-accepted", protect, getMyAccepted);

// Donor: accept a request (atomic)
router.patch("/:id/accept", protect, acceptRequest);

// Donor: mark an accepted request as fulfilled
router.patch("/:id/fulfill", protect, fulfillRequest);

module.exports = router;
