import express from "express";
import { googleLogin, googleCallback } from "./googleAuth.js";

const router = express.Router();

router.get("/auth/google", googleLogin);
router.get("/auth/google/callback", googleCallback);

export default router;
