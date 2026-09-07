import { describe, expect, it } from "vitest";
import { LatestRequest } from "./latest-request";

describe("LatestRequest", () => {
  it("prevents an older refresh from replacing fresh mutation data", () => {
    const requests = new LatestRequest();
    const stale = requests.begin();
    const fresh = requests.begin();

    expect(requests.isCurrent(stale)).toBe(false);
    expect(requests.isCurrent(fresh)).toBe(true);
  });

  it("invalidates pending refreshes when the session closes", () => {
    const requests = new LatestRequest();
    const pending = requests.begin();
    requests.cancelAll();

    expect(requests.isCurrent(pending)).toBe(false);
  });
});
