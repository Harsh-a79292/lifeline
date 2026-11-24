const dns = require("node:dns");
try {
  dns.setServers(["8.8.8.8", "8.8.4.4"]);
} catch (e) {
  console.warn("DNS server configuration skipped:", e.message);
}

require("dotenv").config();

const http = require("http");
const { Server } = require("socket.io");
const jwt = require("jsonwebtoken");
const { getAllowedOrigins } = require("./config/cors");

const app = require("./app");
const connectDB = require("./config/db");

const server = http.createServer(app);

const allowedOrigins = getAllowedOrigins();

const io = new Server(server, {
  cors: {
    origin: allowedOrigins.includes("*") ? "*" : allowedOrigins,
    methods: ["GET", "POST"],
    credentials: true,
  },
});

app.set("io", io);

// Secure Socket.IO Authentication Middleware
io.use((socket, next) => {
  try {
    const token =
      socket.handshake.auth?.token ||
      (socket.handshake.headers?.authorization &&
      socket.handshake.headers.authorization.startsWith("Bearer ")
        ? socket.handshake.headers.authorization.split(" ")[1]
        : null);

    if (!token) {
      return next(new Error("Authentication error: Token required"));
    }

    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    socket.user = decoded; // Contains { id, role }
    next();
  } catch (error) {
    return next(new Error("Authentication error: Invalid or expired token"));
  }
});

io.on("connection", (socket) => {
  console.log(`User connected: ${socket.id} (User: ${socket.user?.id}, Role: ${socket.user?.role})`);

  socket.on("join-donors", (city) => {
    // Only authenticated donors are permitted to join donor alert channels
    if (socket.user?.role !== "donor") {
      return socket.emit("error-message", {
        success: false,
        message: "Only donors are authorized to join donor alert channels",
      });
    }

    if (typeof city === "string" && city.trim()) {
      const room = `donors-${city.trim().toLowerCase()}`;
      socket.join(room);
      console.log(`Donor (${socket.user.id}) joined room: ${room}`);
      socket.emit("joined-room", { room });
    }
  });

  socket.on("disconnect", () => {
    console.log("User disconnected:", socket.id);
  });
});

const PORT = process.env.PORT || 5000;

const startServer = async () => {
  try {
    await connectDB();

    server.listen(PORT, () => {
      console.log(`LifeLine server running on port ${PORT}`);
    });
  } catch (error) {
    console.error("Server startup failed:", error.message);
    process.exit(1);
  }
};

startServer();
