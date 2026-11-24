const getAllowedOrigins = () => {
  if (process.env.CLIENT_ORIGIN) {
    return process.env.CLIENT_ORIGIN.split(",").map((origin) => origin.trim());
  }

  // Sensible development defaults
  return [
    "http://localhost:8501",
    "http://127.0.0.1:8501",
    "http://localhost:3000",
    "http://localhost:5000",
  ];
};

const corsOptions = {
  origin: (origin, callback) => {
    const allowed = getAllowedOrigins();

    // Allow requests with no origin (e.g. mobile apps, curl, Python requests) or wildcard
    if (!origin || allowed.includes("*") || allowed.includes(origin)) {
      return callback(null, true);
    }

    return callback(new Error("CORS policy: Origin not allowed"));
  },
  credentials: true,
  methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization"],
};

module.exports = {
  corsOptions,
  getAllowedOrigins,
};
