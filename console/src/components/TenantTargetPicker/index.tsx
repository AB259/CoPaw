import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Button, Input } from "@agentscope-ai/design";
import { CheckOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

interface TenantTargetPickerProps {
  tenantIds: string[];
  selectedTenantIds: string[];
  onChange: (tenantIds: string[]) => void;
  hint?: ReactNode;
}

export function parseManualTenantIds(input: string): string[] {
  return Array.from(
    new Set(
      input
        .split(/[\s,]+/)
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  );
}

export function TenantTargetPicker({
  tenantIds,
  selectedTenantIds,
  onChange,
  hint,
}: TenantTargetPickerProps) {
  const { t } = useTranslation();
  const [selectedDiscoveredTenantIds, setSelectedDiscoveredTenantIds] =
    useState<string[]>([]);
  const [manualTenantIdsText, setManualTenantIdsText] = useState("");

  const manualTenantIds = useMemo(
    () => parseManualTenantIds(manualTenantIdsText),
    [manualTenantIdsText],
  );

  const mergedTenantIds = Array.from(
    new Set([...selectedDiscoveredTenantIds, ...manualTenantIds]),
  );

  useEffect(() => {
    const discovered = selectedTenantIds.filter((tenantId) =>
      tenantIds.includes(tenantId),
    );
    const manual = selectedTenantIds.filter(
      (tenantId) => !tenantIds.includes(tenantId),
    );
    setSelectedDiscoveredTenantIds(discovered);
    setManualTenantIdsText(manual.join("\n"));
  }, [selectedTenantIds, tenantIds]);

  useEffect(() => {
    onChange(mergedTenantIds);
  }, [mergedTenantIds, onChange]);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 8,
          }}
        >
          <div style={{ fontWeight: 500 }}>{t("skillPool.selectWorkspaces")}</div>
          <div style={{ display: "flex", gap: 8 }}>
            <Button
              size="small"
              onClick={() =>
                setSelectedDiscoveredTenantIds(Array.from(new Set(tenantIds)))
              }
            >
              {t("skillPool.allWorkspaces")}
            </Button>
            <Button size="small" onClick={() => setSelectedDiscoveredTenantIds([])}>
              {t("skills.clearSelection")}
            </Button>
          </div>
        </div>
        {hint ? (
          <div style={{ marginTop: 8, color: "#666", fontSize: 12 }}>{hint}</div>
        ) : null}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: 8,
        }}
      >
        {tenantIds.map((tenantId) => {
          const selected = selectedDiscoveredTenantIds.includes(tenantId);
          return (
            <button
              key={tenantId}
              type="button"
              onClick={() =>
                setSelectedDiscoveredTenantIds(
                  selected
                    ? selectedDiscoveredTenantIds.filter((id) => id !== tenantId)
                    : [...selectedDiscoveredTenantIds, tenantId],
                )
              }
              style={{
                cursor: "pointer",
                borderRadius: 8,
                border: selected ? "1px solid #1677ff" : "1px solid #d9d9d9",
                background: selected ? "#eff6ff" : "#fff",
                padding: "12px 14px",
                textAlign: "left",
                position: "relative",
              }}
            >
              {selected ? (
                <span style={{ position: "absolute", right: 10, top: 8 }}>
                  <CheckOutlined />
                </span>
              ) : null}
              <span>{tenantId}</span>
            </button>
          );
        })}
      </div>

      <div>
        <div style={{ fontWeight: 500 }}>{t("skillPool.manualTenantIds")}</div>
        <div style={{ marginTop: 8, marginBottom: 8, color: "#666", fontSize: 12 }}>
          {t("skillPool.manualTenantHint")}
        </div>
        <Input.TextArea
          rows={4}
          value={manualTenantIdsText}
          onChange={(event) => setManualTenantIdsText(event.target.value)}
          placeholder={t("skillPool.manualTenantPlaceholder")}
        />
      </div>
    </div>
  );
}

export default TenantTargetPicker;
