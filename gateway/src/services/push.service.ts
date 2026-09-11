import axios from "axios";
import supabase from "../config/supabase";

const EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send";

export interface PushPayload {
  title: string;
  body: string;
  data?: Record<string, unknown>;
}

/** Send a push to a list of Expo push tokens (best-effort). */
export async function sendPush(
  tokens: string[],
  payload: PushPayload,
): Promise<void> {
  const messages = tokens
    .filter((t) => t && t.startsWith("ExponentPushToken"))
    .map((to) => ({
      to,
      sound: "default",
      title: payload.title,
      body: payload.body,
      data: payload.data ?? {},
    }));

  if (messages.length === 0) return;

  try {
    await axios.post(EXPO_PUSH_URL, messages, {
      headers: { "Content-Type": "application/json" },
      timeout: 10000,
    });
  } catch (err: any) {
    console.error("[push] send failed:", err?.message);
  }
}

/** Look up a user's device tokens and push to all of them. */
export async function notifyUser(
  userId: string,
  payload: PushPayload,
): Promise<void> {
  const { data } = await supabase
    .from("push_tokens")
    .select("token")
    .eq("user_id", userId);
  await sendPush((data ?? []).map((r: { token: string }) => r.token), payload);
}
