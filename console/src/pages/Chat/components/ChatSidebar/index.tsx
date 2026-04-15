import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { cronJobApi } from '@/api/modules/cronjob';
import type { CronJobSpecOutput } from '@/api/types';
import type { IAgentScopeRuntimeWebUISession } from '@/components/agentscope-chat';
import Style from './style';
import ChatTaskList from '../ChatTaskList';
import sessionApi from '../../sessionApi';
import { DESIGN_TOKENS } from '@/config/designTokens';
import CollapsedToolbar, { type PanelType } from './CollapsedToolbar';
import ExpandablePanel from './ExpandablePanel';

const SIDEBAR_POLL_MS = 10_000;

function HistoryIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle
        cx="8"
        cy="8"
        r="6"
        stroke={DESIGN_TOKENS.colorTextPrimary}
        strokeWidth="1.5"
      />
      <path
        d="M8 4.5V8L10.5 9.5"
        stroke={DESIGN_TOKENS.colorTextPrimary}
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function NewTopicIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
      <path d="M6 1V11M1 6H11" stroke="white" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function SkillMarketIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path
        d="M4.5 3L6 21H18L19.5 3H4.5Z"
        stroke={DESIGN_TOKENS.colorTextSecondary}
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M2 3H22"
        stroke={DESIGN_TOKENS.colorTextSecondary}
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M9 8L10.5 15"
        stroke={DESIGN_TOKENS.colorTextSecondary}
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M15 8L13.5 15"
        stroke={DESIGN_TOKENS.colorTextSecondary}
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function GuideIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <rect
        x="4"
        y="3"
        width="16"
        height="18"
        rx="2"
        stroke={DESIGN_TOKENS.colorTextSecondary}
        strokeWidth="1.5"
      />
      <path
        d="M8 8H16M8 12H13"
        stroke={DESIGN_TOKENS.colorTextSecondary}
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ToggleIcon({ collapsed }: { collapsed: boolean }) {
  return (
    <svg
      width="10"
      height="6"
      viewBox="0 0 10 6"
      fill="none"
      className={`chat-sidebar-history-toggle${collapsed ? ' chat-sidebar-history-toggle--collapsed' : ''}`}
    >
      <path
        d="M1 1L5 5L9 1"
        stroke={DESIGN_TOKENS.colorTextMuted}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export interface ChatSidebarProps {
  onCreateSession?: () => void;
  onTaskClick?: (task: CronJobSpecOutput) => void;
}

function formatTime(raw: string | null | undefined): string {
  if (!raw) return '';
  const date = new Date(raw);
  if (isNaN(date.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
    date.getDate(),
  )} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function isTaskSession(session: IAgentScopeRuntimeWebUISession): boolean {
  const meta = (session as any).meta;
  return meta?.session_kind === 'task';
}

function isVisibleTask(task: CronJobSpecOutput): boolean {
  return task.task_type === 'agent' && Boolean(task.task?.visible_in_my_tasks);
}

export default function ChatSidebar(props: ChatSidebarProps) {
  const { onCreateSession, onTaskClick } = props;
  const navigate = useNavigate();
  const location = useLocation();
  const [historyCollapsed, setHistoryCollapsed] = useState(false);
  const [tasks, setTasks] = useState<CronJobSpecOutput[]>([]);
  const [sessions, setSessions] = useState<IAgentScopeRuntimeWebUISession[]>([]);
  const [collapsed, setCollapsed] = useState(false);
  const [activePanel, setActivePanel] = useState<PanelType>(null);
  const toolbarRef = useRef<HTMLDivElement>(null);

  const currentChatId = location.pathname.match(/^\/chat\/(.+)$/)?.[1] || null;

  const fetchTasks = useCallback(async () => {
    try {
      const data = await cronJobApi.listCronJobs();
      const next = Array.isArray(data) ? data.filter(isVisibleTask) : [];
      setTasks(next);
    } catch {
      setTasks([]);
    }
  }, []);

  const fetchSessions = useCallback(async () => {
    try {
      const list = await sessionApi.getSessionList();
      const next = Array.isArray(list) ? list.filter((session) => !isTaskSession(session)) : [];
      setSessions(next);
    } catch {
      setSessions([]);
    }
  }, []);

  useEffect(() => {
    void fetchTasks();
    void fetchSessions();

    const intervalId = window.setInterval(() => {
      void fetchTasks();
      void fetchSessions();
    }, SIDEBAR_POLL_MS);

    const handleFocusRefresh = () => {
      void fetchTasks();
      void fetchSessions();
    };
    const handleVisibilityRefresh = () => {
      if (document.visibilityState === 'visible') {
        void fetchTasks();
        void fetchSessions();
      }
    };

    window.addEventListener('focus', handleFocusRefresh);
    document.addEventListener('visibilitychange', handleVisibilityRefresh);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener('focus', handleFocusRefresh);
      document.removeEventListener('visibilitychange', handleVisibilityRefresh);
    };
  }, [fetchSessions, fetchTasks, location.pathname]);

  const handleToggleHistory = useCallback(() => {
    setHistoryCollapsed((prev) => !prev);
  }, []);

  const handleSessionClick = useCallback(
    (sessionId: string) => {
      navigate(`/chat/${sessionId}`, { replace: true });
    },
    [navigate],
  );

  const handleNewTopic = useCallback(() => {
    onCreateSession?.();
  }, [onCreateSession]);

  const handleToggleCollapse = useCallback(() => {
    setCollapsed((prev) => !prev);
    setActivePanel(null);
  }, []);

  const handleNewChat = useCallback(() => {
    setActivePanel(null);
    onCreateSession?.();
  }, [onCreateSession]);

  const handleIconClick = useCallback((panel: PanelType) => {
    setActivePanel(panel);
  }, []);

  const handleClosePanel = useCallback(() => {
    setActivePanel(null);
  }, []);

  const handleTaskOpen = useCallback(
    async (task: CronJobSpecOutput) => {
      onTaskClick?.(task);
      const chatId = task.task?.chat_id;
      if (!chatId) return;

      setTasks((prev) =>
        prev.map((item) =>
          item.id === task.id && item.task
            ? {
                ...item,
                task: {
                  ...item.task,
                  unread_execution_count: 0,
                },
              }
            : item,
        ),
      );

      setActivePanel(null);
      navigate(`/chat/${chatId}`, { replace: true });

      try {
        await cronJobApi.markTaskRead(task.id);
      } catch {
        void fetchTasks();
      }
    },
    [fetchTasks, navigate, onTaskClick],
  );

  if (collapsed) {
    return (
      <>
        <Style />
        <div className="chat-sidebar-wrapper chat-sidebar-wrapper--collapsed">
          <div ref={toolbarRef}>
            <CollapsedToolbar
              activePanel={activePanel}
              onIconClick={handleIconClick}
              onNewChat={handleNewChat}
              taskBadgeCount={tasks.length}
            />
          </div>
          <ExpandablePanel
            visible={activePanel === 'tasks'}
            type="tasks"
            onClose={handleClosePanel}
            tasks={tasks}
            sessions={sessions}
            onTaskClick={handleTaskOpen}
            toolbarRef={toolbarRef}
          />
          <ExpandablePanel
            visible={activePanel === 'history'}
            type="history"
            onClose={handleClosePanel}
            tasks={tasks}
            sessions={sessions}
            onTaskClick={handleTaskOpen}
            toolbarRef={toolbarRef}
          />
          <button
            className="chat-sidebar-collapse-toggle"
            onClick={handleToggleCollapse}
            type="button"
            aria-label="展开侧栏"
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path d="M4 2L7 5L4 8" stroke="rgba(0,0,0,0.35)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      <Style />
      <div className="chat-sidebar-wrapper">
        <div className="chat-sidebar">
          <div className="chat-sidebar-content">
            <ChatTaskList tasks={tasks} onTaskClick={handleTaskOpen} />

            <div className="chat-sidebar-history">
              <div
                className="chat-sidebar-history-header"
                onClick={handleToggleHistory}
                role="button"
                tabIndex={0}
              >
                <div className="chat-sidebar-history-title">
                  <HistoryIcon />
                  历史记录({sessions.length})
                </div>
                <ToggleIcon collapsed={historyCollapsed} />
              </div>
              {!historyCollapsed &&
                sessions.map((session) => (
                  <div
                    key={session.id}
                    className="chat-sidebar-history-item"
                    onClick={() => handleSessionClick(session.id!)}
                    role="button"
                    tabIndex={0}
                    style={
                      session.id === currentChatId
                        ? { backgroundColor: 'rgba(55, 105, 252, 0.06)' }
                        : undefined
                    }
                  >
                    <div className="chat-sidebar-history-item-title">
                      {session.name || '新会话'}
                    </div>
                    <div className="chat-sidebar-history-item-time">
                      {formatTime((session as any).createdAt)}
                    </div>
                  </div>
                ))}
            </div>
          </div>

          <div className="chat-sidebar-new-topic">
            <button
              className="chat-sidebar-new-topic-btn"
              onClick={handleNewTopic}
              type="button"
            >
              <NewTopicIcon />
              新建聊天
            </button>
          </div>

          <div className="chat-sidebar-footer">
            <div className="chat-sidebar-footer-item">
              <SkillMarketIcon />
              skill市场
            </div>
            <div className="chat-sidebar-footer-divider" />
            <div className="chat-sidebar-footer-item">
              <GuideIcon />
              操作指南
            </div>
          </div>
        </div>
        <button
          className="chat-sidebar-collapse-toggle"
          onClick={handleToggleCollapse}
          type="button"
          aria-label="收起侧栏"
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
            <path d="M6 2L3 5L6 8" stroke="rgba(0,0,0,0.35)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
    </>
  );
}
