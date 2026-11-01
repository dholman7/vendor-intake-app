import { expect, type APIResponse } from "@playwright/test";

/**
 * Asserts a response's status with its body attached to the failure, then returns the parsed
 * JSON body (or null for an empty one). A bare "expected 201, received 422" hides the reason.
 */
export async function expectStatus<T = any>(response: APIResponse, status: number): Promise<T> {
  const text = await response.text();
  expect(response.status(), `${response.url()}\n${text}`).toBe(status);
  return (text ? JSON.parse(text) : null) as T;
}
