import { apiGet, apiPatch, apiPost } from "./client";
import type {
  ConfigStatusResponse,
  SetupConfigPatch,
  SetupConfigUpdateResponse,
  SetupEditableConfigResponse,
  SetupValidationResponse,
} from "./types";

export function getConfigStatus() {
  return apiGet<ConfigStatusResponse>("/api/config/status");
}

export function checkConfigStatus() {
  return apiPost<ConfigStatusResponse>("/api/config/check");
}

export function getEditableConfig() {
  return apiGet<SetupEditableConfigResponse>("/api/config/editable");
}

export function validateSetupConfig(patch: SetupConfigPatch) {
  return apiPost<SetupValidationResponse>("/api/config/validate", patch);
}

export function saveSetupConfig(patch: SetupConfigPatch) {
  return apiPatch<SetupConfigUpdateResponse>("/api/config/editable", patch);
}
