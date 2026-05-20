import { useEffect, useState } from "react";
import { Alert, Button, Card, Result, Space, Spin, Switch, Tag } from "antd";
import { useTranslation } from "react-i18next";

import { PageHeader } from "@/components/PageHeader";
import { useAppMessage } from "@/hooks/useAppMessage";
import { sourceSystemConfigApi } from "@/api/modules/sourceSystemConfig";
import type {
  CurrentSourceSystemConfigResponse,
  SourceSystemConfig,
} from "@/api/types/sourceSystemConfig";
import { useIframeStore } from "@/stores/iframeStore";
import { useSourceSystemConfigStore } from "@/stores/sourceSystemConfigStore";
import { DEFAULT_SOURCE_ID } from "@/constants/identity";

import {
  CURRENT_SOURCE_SYSTEM_CONFIG_SWITCHES,
  readRegisteredSwitchValue,
  writeRegisteredSwitchValue,
} from "./registry";
import styles from "./index.module.less";

function formatUpdatedAt(value?: string | null): string {
  if (!value) {
    return "未保存";
  }
  return value;
}

export default function SystemConfigPage() {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const isSuperManager = useIframeStore((state) => state.isSuperManager);
  const manager = useIframeStore((state) => state.manager);
  const activeSourceId =
    useIframeStore((state) => state.source) || DEFAULT_SOURCE_ID;
  const loadEffectiveConfig = useSourceSystemConfigStore(
    (state) => state.loadEffectiveConfig,
  );
  const canManage = isSuperManager || manager;
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [record, setRecord] =
    useState<CurrentSourceSystemConfigResponse | null>(null);
  const [draftConfig, setDraftConfig] = useState<SourceSystemConfig>({});

  useEffect(() => {
    if (!canManage) {
      setLoading(false);
      setError(null);
      setRecord(null);
      setDraftConfig({});
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    setRecord(null);

    sourceSystemConfigApi
      .getCurrent()
      .then((response) => {
        if (cancelled) {
          return;
        }
        setRecord(response);
        setDraftConfig(response.config);
      })
      .catch((requestError) => {
        if (cancelled) {
          return;
        }
        setError(
          requestError instanceof Error
            ? requestError.message
            : String(requestError),
        );
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [activeSourceId, canManage]);

  if (!canManage) {
    return (
      <div className={styles.systemConfigPage}>
        <PageHeader
          parent={t("nav.settings")}
          current={t("nav.currentSourceConfig", {
            defaultValue: "当前 Source 配置",
          })}
        />
        <div className={styles.centerState}>
          <Result
            status="403"
            title="403"
            subTitle={t("sourceSystemConfigPage.forbidden", {
              defaultValue: "仅管理员可访问当前 Source 系统配置页面。",
            })}
          />
        </div>
      </div>
    );
  }

  const handleSwitchChange = (key: string, checked: boolean) => {
    const definition = CURRENT_SOURCE_SYSTEM_CONFIG_SWITCHES.find(
      (item) => item.key === key,
    );
    if (!definition) {
      return;
    }
    setDraftConfig((previous) =>
      writeRegisteredSwitchValue(previous, definition, checked),
    );
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const nextRecord = await sourceSystemConfigApi.updateCurrent({
        config: draftConfig,
      });
      setRecord(nextRecord);
      setDraftConfig(nextRecord.config);
      await loadEffectiveConfig(activeSourceId);
      message.success(
        t("sourceSystemConfigPage.saveSuccess", {
          defaultValue: "当前 Source 配置已保存",
        }),
      );
    } catch (requestError) {
      const nextError =
        requestError instanceof Error
          ? requestError.message
          : String(requestError);
      setError(nextError);
      message.error(nextError);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setSaving(true);
    setError(null);
    try {
      await sourceSystemConfigApi.deleteCurrent();
      const nextRecord = await sourceSystemConfigApi.getCurrent();
      setRecord(nextRecord);
      setDraftConfig(nextRecord.config);
      await loadEffectiveConfig(activeSourceId);
      message.success(
        t("sourceSystemConfigPage.deleteSuccess", {
          defaultValue: "当前 Source 配置已恢复默认态",
        }),
      );
    } catch (requestError) {
      const nextError =
        requestError instanceof Error
          ? requestError.message
          : String(requestError);
      setError(nextError);
      message.error(nextError);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.systemConfigPage}>
      <PageHeader
        parent={t("nav.settings")}
        current={t("nav.currentSourceConfig", {
          defaultValue: "当前 Source 配置",
        })}
        subRow={
          <Space size={8}>
            <Tag color="blue">{activeSourceId}</Tag>
            <Tag color={record?.is_default ? "default" : "gold"}>
              {record?.is_default
                ? t("sourceSystemConfigPage.defaultState", {
                    defaultValue: "继承默认值",
                  })
                : t("sourceSystemConfigPage.overrideState", {
                    defaultValue: "存在显式覆盖",
                  })}
            </Tag>
          </Space>
        }
      />
      <div className={styles.pageBody}>
        {error ? (
          <Alert
            type="error"
            showIcon
            message={t("sourceSystemConfigPage.loadFailed", {
              defaultValue: "当前 Source 配置加载失败",
            })}
            description={error}
          />
        ) : null}

        {loading ? (
          <div className={styles.centerState}>
            <Spin size="large" />
          </div>
        ) : (
          <>
            <Card className={styles.metaCard}>
              <div className={styles.metaGrid}>
                <div>
                  <span className={styles.metaLabel}>
                    {t("sourceSystemConfigPage.sourceLabel", {
                      defaultValue: "当前 Source",
                    })}
                  </span>
                  <span className={styles.metaValue}>{activeSourceId}</span>
                </div>
                <div>
                  <span className={styles.metaLabel}>
                    {t("sourceSystemConfigPage.versionLabel", {
                      defaultValue: "原始配置版本",
                    })}
                  </span>
                  <span className={styles.metaValue}>
                    {record?.version ?? 0}
                  </span>
                </div>
                <div>
                  <span className={styles.metaLabel}>
                    {t("sourceSystemConfigPage.updatedByLabel", {
                      defaultValue: "最近修改人",
                    })}
                  </span>
                  <span className={styles.metaValue}>
                    {record?.updated_by || "未保存"}
                  </span>
                </div>
                <div>
                  <span className={styles.metaLabel}>
                    {t("sourceSystemConfigPage.updatedAtLabel", {
                      defaultValue: "最近修改时间",
                    })}
                  </span>
                  <span className={styles.metaValue}>
                    {formatUpdatedAt(record?.updated_at)}
                  </span>
                </div>
              </div>
            </Card>

            <Card
              className={styles.switchCard}
              title={t("sourceSystemConfigPage.switchesTitle", {
                defaultValue: "受控功能开关",
              })}
            >
              <div className={styles.switchList}>
                {CURRENT_SOURCE_SYSTEM_CONFIG_SWITCHES.map((definition) => (
                  <div
                    key={definition.key}
                    className={styles.switchRow}
                  >
                    <div className={styles.switchCopy}>
                      <span className={styles.switchTitle}>
                        {definition.title}
                      </span>
                      <span className={styles.switchDescription}>
                        {definition.description}
                      </span>
                    </div>
                    <Switch
                      checked={readRegisteredSwitchValue(
                        draftConfig,
                        definition,
                      )}
                      onChange={(checked) =>
                        handleSwitchChange(definition.key, checked)
                      }
                    />
                  </div>
                ))}
              </div>
            </Card>

            <div className={styles.actionRow}>
              <Button
                danger
                onClick={handleDelete}
                disabled={saving || record?.is_default}
              >
                {t("common.delete")}
              </Button>
              <Button
                type="primary"
                loading={saving}
                onClick={handleSave}
              >
                {t("common.save")}
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
