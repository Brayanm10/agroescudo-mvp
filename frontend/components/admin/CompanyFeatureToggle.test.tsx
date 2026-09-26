import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CompanyFeatureToggle } from "./CompanyFeatureToggle";
import type { Company } from "@/lib/types";

function company(features: string[]): Company {
  return {
    id: 7,
    name: "Empresa QA",
    tax_id: null,
    type: "acopiador",
    city: null,
    contact_name: null,
    contact_email: null,
    contact_phone: null,
    is_active: true,
    created_at: "2026-09-25T00:00:00Z",
    updated_at: null,
    features,
  };
}

describe("CompanyFeatureToggle", () => {
  it("shows Pluviometry enabled for an entitled company", () => {
    const markup = renderToStaticMarkup(<CompanyFeatureToggle company={company(["PLUVIOMETRY"])} token="token" onChanged={() => undefined} />);
    expect(markup).toContain("Módulos habilitados");
    expect(markup).toContain('aria-checked="true"');
    expect(markup).toContain(">ON<");
  });

  it("shows Pluviometry disabled without exposing company data", () => {
    const markup = renderToStaticMarkup(<CompanyFeatureToggle company={company([])} token="token" onChanged={() => undefined} />);
    expect(markup).toContain('aria-checked="false"');
    expect(markup).toContain(">OFF<");
  });
});
