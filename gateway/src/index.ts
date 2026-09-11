import dotenv from "dotenv";
dotenv.config();
import express from "express";
import helmet from "helmet";
import cors from "cors";
import morgan from "morgan";
import rateLimit from "express-rate-limit";

import authRoutes from "./routes/auth.routes";
import searchRoutes from "./routes/search.routes";
import historyRoutes from "./routes/history.routes";
import watchlistRoutes from "./routes/watchlist.routes";
import movieRoutes from "./routes/movie.routes";
import notificationRoutes from "./routes/notifications.routes";
import { errorHandler } from "./middleware/error.middleware";

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(cors());
app.use(morgan("dev"));
app.use(express.json());

const limiter = rateLimit({
  windowMs: Number(process.env.RATE_LIMIT_WINDOW_MS) || 15 * 60 * 1000,
  max: Number(process.env.RATE_LIMIT_MAX_REQUESTS) || 100,
  message: { error: "Too many requests, please try again later." },
});
app.use("/api/", limiter);

app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    service: "gist-gateway",
    timestamp: new Date().toISOString(),
  });
});



app.use("/api/auth", authRoutes);
app.use("/api/search", searchRoutes);
app.use("/api/history", historyRoutes);
app.use("/api/watchlist", watchlistRoutes);
app.use("/api/movie", movieRoutes);
app.use("/api/notifications", notificationRoutes);

app.use((req, res) => {
  res.status(404).json({ error: `Route ${req.method} ${req.path} not found` });
});

app.use(errorHandler);

app.listen(PORT, () => {
  console.log(`Recall running on port ${PORT}`);
});

export default app;
