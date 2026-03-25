import { apiRequest } from "./client";
import {
  clearAuthStorage,
  getAccessToken,
  getStoredUser,
  setAccessToken,
  setStoredUser,
} from "../utils/authStorage";
import type {
  AuthSessionResponse,
  AuthUser,
  DriverLoginPayload,
  DriverRegistrationPayload,
  EmailVerificationStatusResponse,
  PhoneVerificationStatusResponse,
  ResendVerificationPayload,
  VerifyPhoneOtpPayload,
} from "@shared/types/auth";

type ApiEnvelope<T> = {
  success?: boolean;
  message?: string | null;
  data?: T;
};

type UnknownRecord = Record<string, unknown>;

function unwrapPayload<T>(payload: T | ApiEnvelope<T>): T {
  if (
    payload &&
    typeof payload === "object" &&
    "data" in (payload as UnknownRecord) &&
    (payload as ApiEnvelope<T>).data !== undefined
  ) {
    return (payload as ApiEnvelope<T>).data as T;
  }

  return payload as T;
}

function toOptionalString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function normalizeUser(payload: unknown): AuthUser {
  const source = (payload ?? {}) as UnknownRecord;
  return {
    userId: String(source.userId ?? source.user_id ?? source.id ?? ""),
    fullName: toOptionalString(source.fullName ?? source.full_name ?? source.name),
    email: toOptionalString(source.email),
    phone: toOptionalString(source.phone ?? source.phone_number),
    role: toOptionalString(source.role),
    emailVerified: Boolean(source.emailVerified ?? source.email_verified),
    phoneVerified: Boolean(source.phoneVerified ?? source.phone_verified),
  };
}

function normalizeSession(payload: unknown): AuthSessionResponse {
  const source = (payload ?? {}) as UnknownRecord;
  return {
    accessToken: String(source.accessToken ?? source.access_token ?? ""),
    refreshToken: toOptionalString(source.refreshToken ?? source.refresh_token),
    user: normalizeUser(source.user),
  };
}

function mergeStoredUser(user: AuthUser): AuthUser {
  const storedUser = getStoredUser();
  return {
    ...storedUser,
    ...user,
    userId: user.userId || storedUser?.userId || "",
  };
}

function persistSession(session: AuthSessionResponse): AuthSessionResponse {
  if (session.accessToken) {
    setAccessToken(session.accessToken);
  }
  if (session.user.userId) {
    setStoredUser(mergeStoredUser(session.user));
  }
  return session;
}

async function setDriverPresence(isOnline: boolean): Promise<void> {
  try {
    await apiRequest<unknown>("/drivers/me/availability", {
      method: "POST",
      body: {
        is_online: isOnline,
        is_available: isOnline,
      },
    });
  } catch {
    // Keep auth flows usable even if presence sync fails.
  }
}

export async function sendDriverPresenceHeartbeat(): Promise<void> {
  try {
    await apiRequest<unknown>("/drivers/me/presence/heartbeat", {
      method: "POST",
    });
  } catch {
    // Heartbeat expiry is recoverable; the next availability change or login can restore presence.
  }
}

export async function registerDriver(
  payload: DriverRegistrationPayload,
): Promise<AuthSessionResponse | { success: true }> {
  const response = await apiRequest<unknown>("/auth/signup", {
    method: "POST",
    body: {
      email: payload.email,
      phone_number: payload.phone,
      password: payload.password,
      role: "DRIVER",
    },
  });
  const data = unwrapPayload(response);
  if (
    data &&
    typeof data === "object" &&
    ("access_token" in (data as UnknownRecord) || "accessToken" in (data as UnknownRecord))
  ) {
    return persistSession(normalizeSession(data));
  }
  return { success: true };
}

export async function loginDriver(payload: DriverLoginPayload): Promise<AuthSessionResponse> {
  const response = await apiRequest<unknown>("/auth/login", {
    method: "POST",
    body: {
      email_or_phone: payload.identifier,
      password: payload.password,
    },
  });

  const session = persistSession(normalizeSession(unwrapPayload(response)));
  await setDriverPresence(true);
  return session;
}

export async function getCurrentDriverProfile(): Promise<AuthUser> {
  const response = await apiRequest<unknown>("/auth/me", { method: "GET" });
  const user = mergeStoredUser(normalizeUser(unwrapPayload(response)));
  if (user.userId) {
    setStoredUser(user);
  }
  return user;
}

export async function resendDriverEmailVerification(
  payload?: ResendVerificationPayload,
): Promise<{ success: true }> {
  await apiRequest<unknown>("/driver/verify-email/resend", {
    method: "POST",
    body: payload ?? {},
  });
  return { success: true };
}

export async function getDriverEmailVerificationStatus(): Promise<EmailVerificationStatusResponse> {
  const response = await apiRequest<unknown>("/driver/verify-email/status", { method: "GET" });
  const source = unwrapPayload(response) as UnknownRecord;
  return {
    emailVerified: Boolean(source.emailVerified ?? source.email_verified),
  };
}

export async function resendDriverPhoneOtp(
  payload: ResendVerificationPayload,
): Promise<{ success: true }> {
  await apiRequest<unknown>("/driver/verify-phone/resend", {
    method: "POST",
    body: payload,
  });
  return { success: true };
}

export async function verifyDriverPhoneOtp(
  payload: VerifyPhoneOtpPayload,
): Promise<{ success: true }> {
  await apiRequest<unknown>("/driver/verify-phone/confirm", {
    method: "POST",
    body: payload,
  });
  return { success: true };
}

export async function getDriverPhoneVerificationStatus(): Promise<PhoneVerificationStatusResponse> {
  const response = await apiRequest<unknown>("/driver/verify-phone/status", { method: "GET" });
  const source = unwrapPayload(response) as UnknownRecord;
  return {
    phoneVerified: Boolean(source.phoneVerified ?? source.phone_verified),
  };
}

export function clearSession(): void {
  clearAuthStorage();
}

export function getStoredToken(): string | null {
  return getAccessToken();
}

export function markCurrentDriverOffline(): Promise<void> {
  return setDriverPresence(false);
}

export { getStoredUser };
