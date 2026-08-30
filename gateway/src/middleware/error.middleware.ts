import { Request, Response, NextFunction } from "express";

// 1. Extend the standard Error interface to recognize status codes
export interface CustomError extends Error {
  statusCode?: number;
  status?: number;
}

/**
 * Global Express Error Handling Middleware.
 * Must take exactly 4 arguments so Express recognizes it as an error handler.
 */
export function errorHandler(
  err: CustomError,
  req: Request,
  res: Response,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  next: NextFunction,
): void {
  console.error(`[ERROR] ${req.method} ${req.path}:`, err.message);

  const statusCode = err.statusCode || err.status || 500;

  res.status(statusCode).json({
    error: err.message || "Internal server error",
    ...(process.env.NODE_ENV === "development" && { stack: err.stack }),
  });
}


