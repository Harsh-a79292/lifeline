const express = require("express");
const helmet = require("helmet");
const cors = require("cors");
const { corsOptions } = require("./config/cors");
const { apiLimiter } = require("./middleware/rateLimiter");

const app = express();

// Security Headers
app.use(helmet());

// Strict Configurable CORS
app.use(cors(corsOptions));

// Body Parser
app.use(express.json());

// Apply Rate Limiter to all /api endpoints
app.use("/api", apiLimiter);

// Root & Health Endpoints
app.get("/", (req, res) => {
  res.json({
    success: true,
    message: "LifeLine API is running!",
  });
});

app.get("/api/health", (req, res) => {
  res.json({
    success: true,
    status: "healthy",
    project: "LifeLine",
  });
});

// Application Routes
app.use("/api/requests", require("./routes/requestRoutes"));
app.use("/api/auth", require("./routes/authRoutes"));

// 404 Handler for undefined routes
app.use((req, res) => {
  res.status(404).json({
    success: false,
    message: "API endpoint not found",
  });
});

// Centralized Generic Error Handler
app.use((err, req, res, next) => {
  console.error("Unhandled Application Error:", err.message);

  if (err.message && err.message.includes("CORS policy")) {
    return res.status(403).json({
      success: false,
      message: "Access forbidden by CORS policy",
    });
  }

  return res.status(err.status || 500).json({
    success: false,
    message: "An internal server error occurred. Please try again later.",
  });
});

module.exports = app;
