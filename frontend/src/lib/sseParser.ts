/**
 * Pure SSE event parser for the A2A streaming protocol.
 *
 * Extracts the event-parsing logic from useAgentChat's `executeSend` onmessage
 * handler into stateless, testable functions. All side-effects are described
 * declaratively in the returned `ParseResult` rather than executed inline.
 */

import type { TraceStep } from '@/hooks/useAgentChat';
import {
  extractMessageMetadataFromEvent,
  extractMessageMetadataFromParts,
  type MessageMetadata,
} from '@/lib/chatMetadata';
import { validateWidgetDefinition } from '@/types/widgets';

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/** Mutable accumulator that tracks streaming state across SSE events. */
export interface SSEAccumulator {
  agentText: string;
  currentTraces: TraceStep[];
  currentWidget: unknown | null;
  agentName: string;
  isThinking: boolean;
  directorProgress: { step: string; total: number; current: number } | null;
  metadata: Record<string, unknown> | null;
  /** De-duplication set for director_progress stages. */
  seenProgressStages: Set<string>;
  /** Whether an error event has been received during this stream. */
  hasError: boolean;
  /** Interaction ID captured from the interaction_complete SSE event. */
  interactionId: string | null;
}

export interface ParsedSideEffect {
  type: 'save_widget' | 'focus_widget' | 'workspace_activity' | 'error_activity' | 'long_task';
  payload: unknown;
}

export interface LongTaskEvent {
  eventType: 'long_task_started' | 'long_task_progress' | 'long_task_completed';
  jobId: string;
  kind?: string;
  status?: string;
  progressPct?: number | null;
  message?: string | null;
  pollUrl?: string | null;
  estimatedDurationS?: number | null;
  result?: unknown;
  error?: string | null;
}

/** Result of parsing a single SSE event. */
export interface ParseResult {
  /** New text fragment to append (null if no text in this event). */
  textDelta: string | null;
  /** Accumulated full text so far. */
  fullText: string;
  /** Raw widget data if a valid widget was found (pre-workspace-defaults). */
  widgetFound: unknown | null;
  /** Updated traces array. */
  traces: TraceStep[];
  /** Agent name if changed by this event, null otherwise. */
  agentName: string | null;
  /** Whether the agent is still "thinking" (no content yet). */
  isThinking: boolean;
  /** Metadata extracted from this event, if any. */
  metadata: MessageMetadata | null;
  /** Declarative side effects that should be executed by the caller. */
  sideEffects: ParsedSideEffect[];
  /** If the event was an error, the error text. */
  errorText: string | null;
  /** Whether this event was a ping / no-op. */
  skipped: boolean;
  /** Interaction ID from an interaction_complete event, null otherwise. */
  interactionId: string | null;
}

// ---------------------------------------------------------------------------
// Director progress stage labels (mirrored from useAgentChat)
// ---------------------------------------------------------------------------

const DIRECTOR_STAGE_LABELS: Record<string, string> = {
  planning_started: 'Planning storyboard',
  planning_done: 'Storyboard ready',
  assets_done: 'Scene assets generated',
  rendering_started: 'Rendering final video',
  completed: 'Video completed',
  failed: 'Video generation failed',
};

const LONG_TASK_EVENT_TYPES = new Set([
  'long_task_started',
  'long_task_progress',
  'long_task_completed',
]);

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

/**
 * Create a fresh accumulator for a new streaming session.
 *
 * @param defaultAgentName - The display name to use when the author is
 *   ExecutiveAgent or not yet known.
 */
export function createAccumulator(defaultAgentName: string = 'Pikar AI'): SSEAccumulator {
  return {
    agentText: '',
    currentTraces: [],
    currentWidget: null,
    agentName: defaultAgentName,
    isThinking: true,
    directorProgress: null,
    metadata: null,
    seenProgressStages: new Set(),
    hasError: false,
    interactionId: null,
  };
}

function extractWidgetCandidate(payload: unknown): Record<string, unknown> | null {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return null
  }

  const candidate = payload as Record<string, unknown>
  if (validateWidgetDefinition(candidate)) {
    return candidate
  }

  const wrappedWidget = candidate.widget
  if (validateWidgetDefinition(wrappedWidget)) {
    return wrappedWidget as Record<string, unknown>
  }

  if (candidate.result && typeof candidate.result === 'object' && candidate.result !== null) {
    return extractWidgetCandidate(candidate.result)
  }

  return null
}

function toLongTaskEvent(data: Record<string, unknown>): LongTaskEvent | null {
  const eventType = typeof data.event_type === 'string' ? data.event_type : '';
  if (!LONG_TASK_EVENT_TYPES.has(eventType)) return null;

  const jobId = typeof data.job_id === 'string' ? data.job_id : '';
  if (!jobId) return null;

  const progressPct =
    typeof data.progress_pct === 'number' && Number.isFinite(data.progress_pct)
      ? data.progress_pct
      : null;
  const estimatedDurationS =
    typeof data.estimated_duration_s === 'number' && Number.isFinite(data.estimated_duration_s)
      ? data.estimated_duration_s
      : null;

  return {
    eventType: eventType as LongTaskEvent['eventType'],
    jobId,
    kind: typeof data.kind === 'string' ? data.kind : undefined,
    status: typeof data.status === 'string' ? data.status : undefined,
    progressPct,
    message: typeof data.message === 'string' ? data.message : null,
    pollUrl: typeof data.poll_url === 'string' ? data.poll_url : null,
    estimatedDurationS,
    result: data.result,
    error: typeof data.error === 'string' ? data.error : null,
  };
}

function describeLongTask(event: LongTaskEvent): string {
  const kind = event.kind || 'background task';
  if (event.eventType === 'long_task_started') {
    const eta =
      typeof event.estimatedDurationS === 'number'
        ? ` (~${Math.max(1, Math.round(event.estimatedDurationS / 60))} min)`
        : '';
    return `Started ${kind}${eta}`;
  }
  if (event.eventType === 'long_task_completed') {
    return event.error ? `Failed: ${event.error}` : `Completed ${kind}`;
  }
  const pct =
    typeof event.progressPct === 'number'
      ? ` ${Math.max(0, Math.min(100, Math.round(event.progressPct)))}%`
      : '';
  return event.message || `Running ${kind}${pct}`;
}

// ---------------------------------------------------------------------------
// Core parser
// ---------------------------------------------------------------------------

/**
 * Parse a single SSE event payload and update the accumulator in place.
 *
 * This is a pure-ish function: it mutates `accumulator` for efficiency but
 * returns a `ParseResult` that the caller can use to decide what React state
 * updates or DOM side effects to perform.
 *
 * @param eventData - The raw `event.data` string from the SSE message.
 * @param accumulator - The mutable accumulator tracking this stream.
 * @param defaultAgentName - Fallback display name for ExecutiveAgent.
 * @returns A ParseResult describing what changed.
 */
export function parseSSEEvent(
  eventData: string,
  accumulator: SSEAccumulator,
  defaultAgentName: string = 'Pikar AI',
): ParseResult {
  const result: ParseResult = {
    textDelta: null,
    fullText: accumulator.agentText,
    widgetFound: null,
    traces: accumulator.currentTraces,
    agentName: null,
    isThinking: accumulator.isThinking,
    metadata: null,
    sideEffects: [],
    errorText: null,
    skipped: false,
    interactionId: null,
  };

  // ------- Parse JSON -------
  let data: Record<string, unknown>;
  try {
    data = JSON.parse(eventData) as Record<string, unknown>;
  } catch {
    // Malformed JSON — skip silently (matches existing console.error behaviour
    // but the caller can log if desired).
    result.skipped = true;
    return result;
  }

  // ------- Interaction complete (feedback loop) -------
  if (data.type === 'interaction_complete') {
    const iid = typeof data.interaction_id === 'string' ? data.interaction_id : null;
    accumulator.interactionId = iid;
    result.interactionId = iid;
    return result;
  }

  // ------- Long-running job handoff / polling progress -------
  const longTaskEvent = toLongTaskEvent(data);
  if (longTaskEvent) {
    const traceContent = describeLongTask(longTaskEvent);
    const dedupeKey = `long_task:${longTaskEvent.jobId}:${longTaskEvent.eventType}:${longTaskEvent.status ?? ''}:${longTaskEvent.progressPct ?? ''}:${traceContent}`;

    if (!accumulator.seenProgressStages.has(dedupeKey)) {
      accumulator.seenProgressStages.add(dedupeKey);
      accumulator.currentTraces.push({
        type:
          longTaskEvent.eventType === 'long_task_completed'
            ? 'tool_output'
            : 'tool_use',
        toolName: longTaskEvent.kind || 'Background task',
        content: traceContent,
      });
      result.traces = [...accumulator.currentTraces];
    }

    if (longTaskEvent.eventType === 'long_task_completed' && !longTaskEvent.error) {
      const candidate = extractWidgetCandidate(longTaskEvent.result);
      if (candidate) {
        accumulator.currentWidget = candidate;
        result.widgetFound = candidate;
        result.sideEffects.push({
          type: 'save_widget',
          payload: candidate,
        });
        result.sideEffects.push({
          type: 'focus_widget',
          payload: candidate,
        });
      }
    }

    result.sideEffects.push({
      type: 'long_task',
      payload: longTaskEvent,
    });
    accumulator.isThinking = false;
    result.isThinking = false;
    return result;
  }

  // ------- Director progress -------
  if (data.event_type === 'director_progress') {
    const stage = typeof data.stage === 'string' ? data.stage : 'unknown';
    const label = DIRECTOR_STAGE_LABELS[stage] || `Progress: ${stage}`;
    const payload = data.payload as Record<string, unknown> | undefined;
    const payloadText =
      payload && Object.keys(payload).length > 0 ? ` (${JSON.stringify(payload)})` : '';
    const traceContent = `${label}${payloadText}`;
    const dedupeKey = `${stage}:${payloadText}`;

    if (!accumulator.seenProgressStages.has(dedupeKey)) {
      accumulator.seenProgressStages.add(dedupeKey);
      const trace: TraceStep = {
        type: stage === 'completed' || stage === 'failed' ? 'tool_output' : 'tool_use',
        toolName: 'AI Director',
        content: traceContent,
      };
      accumulator.currentTraces.push(trace);
      result.traces = [...accumulator.currentTraces];
    }

    // When the storyboard plan is ready, surface the scene-by-scene captions
    // as a structured `director_storyboard` widget so users can read the
    // plan instead of scraping JSON out of the trace drawer.
    if (
      stage === 'planning_done' &&
      payload &&
      Array.isArray(payload.storyboard_captions) &&
      payload.storyboard_captions.length > 0
    ) {
      const rawCaptions = payload.storyboard_captions as unknown[];
      const captions = rawCaptions
        .map((entry, idx) => {
          if (typeof entry === 'string') {
            return { scene: idx + 1, caption: entry };
          }
          if (entry && typeof entry === 'object') {
            const obj = entry as Record<string, unknown>;
            const caption =
              typeof obj.caption === 'string'
                ? obj.caption
                : typeof obj.text === 'string'
                  ? obj.text
                  : '';
            const scene =
              typeof obj.scene === 'number' ? obj.scene : idx + 1;
            const duration =
              typeof obj.duration === 'number' ? obj.duration : undefined;
            return caption ? { scene, caption, ...(duration !== undefined ? { duration } : {}) } : null;
          }
          return null;
        })
        .filter((c): c is { scene: number; caption: string; duration?: number } => c !== null);

      if (captions.length > 0) {
        const sceneCount =
          typeof payload.scene_count === 'number'
            ? payload.scene_count
            : captions.length;
        const videoPrompt =
          typeof payload.video_prompt === 'string' ? payload.video_prompt : undefined;
        const storyboardWidget = {
          type: 'director_storyboard',
          title: 'Storyboard',
          dismissible: true,
          data: {
            captions,
            scene_count: sceneCount,
            ...(videoPrompt ? { video_prompt: videoPrompt } : {}),
          },
        };
        accumulator.currentWidget = storyboardWidget;
        result.widgetFound = storyboardWidget;
        result.sideEffects.push({
          type: 'save_widget',
          payload: storyboardWidget,
        });
        result.sideEffects.push({
          type: 'focus_widget',
          payload: storyboardWidget,
        });
      }
    }

    // Director progress events carry no text / author — return.
    return result;
  }

  // ------- Tool-call boundary progress (start / end) -------
  // Backend emits these from ADK before/after tool callbacks so the trace
  // drawer can show a live "running <tool_name>" indicator instead of a
  // silent gap during multi-minute tool runs.
  if (data.event_type === 'tool_call_start' || data.event_type === 'tool_call_end') {
    const toolName =
      typeof data.tool_name === 'string' && data.tool_name
        ? data.tool_name
        : 'tool';
    const isEnd = data.event_type === 'tool_call_end';

    if (isEnd) {
      const status = typeof data.status === 'string' ? data.status : 'ok';
      const durationMs =
        typeof data.duration_ms === 'number' ? data.duration_ms : null;
      const durationLabel =
        durationMs !== null
          ? durationMs >= 1000
            ? ` (${(durationMs / 1000).toFixed(1)}s)`
            : ` (${durationMs}ms)`
          : '';
      const statusPrefix = status === 'error' ? 'Failed' : 'Done';
      const trace: TraceStep = {
        type: 'tool_output',
        toolName,
        content: `${statusPrefix}${durationLabel}`,
      };
      accumulator.currentTraces.push(trace);
    } else {
      const trace: TraceStep = {
        type: 'tool_use',
        toolName,
        content: 'Running…',
      };
      accumulator.currentTraces.push(trace);
    }
    result.traces = [...accumulator.currentTraces];
    // Boundary events carry no text / author — return.
    return result;
  }

  // ------- Error -------
  if (data.error) {
    accumulator.hasError = true;
    const errorText =
      typeof data.error === 'string'
        ? data.error
        : 'Agent encountered an internal error. Please try again.';
    result.errorText = errorText;

    result.sideEffects.push({
      type: 'error_activity',
      payload: {
        agentName: accumulator.agentName,
        text: errorText,
        traces: [...accumulator.currentTraces],
      },
    });
    return result;
  }

  // ------- Author -------
  if (data.author && data.author !== 'user' && data.author !== 'system') {
    const rawAuthor = data.author as string;
    const resolvedName = rawAuthor === 'ExecutiveAgent' ? defaultAgentName : rawAuthor;
    if (resolvedName !== accumulator.agentName) {
      accumulator.agentName = resolvedName;
      result.agentName = resolvedName;
    }
  }

  // ------- Content parts -------
  let newText = '';
  if (
    data.content &&
    typeof data.content === 'object' &&
    !Array.isArray(data.content) &&
    (data.content as Record<string, unknown>).parts
  ) {
    const parts = (data.content as Record<string, unknown>).parts as unknown[];

    // Metadata from parts
    const extractedMetadata = extractMessageMetadataFromParts(parts);
    if (extractedMetadata) {
      accumulator.metadata = extractedMetadata;
      result.metadata = extractedMetadata;
    }

    for (const part of parts) {
      if (!part || typeof part !== 'object') continue;
      const p = part as Record<string, unknown>;

      // Text
      if (typeof p.text === 'string') {
        newText += p.text;
      }

      // Widget in part
      if (p.widget && validateWidgetDefinition(p.widget)) {
        accumulator.currentWidget = p.widget;
        result.widgetFound = p.widget;
      }

      // Widget in functionResponse / function_response
      const fr =
        (p.function_response as Record<string, unknown> | undefined) ??
        (p.functionResponse as Record<string, unknown> | undefined);
      if (fr && !accumulator.currentWidget) {
        const response = (fr.response ?? fr.response_data) as
          | Record<string, unknown>
          | undefined;
        const candidate = extractWidgetCandidate(response);
        if (candidate) {
          accumulator.currentWidget = candidate;
          result.widgetFound = candidate;
        }
      }
    }
  } else if (typeof data.content === 'string') {
    newText = data.content;
  }

  // Fallback metadata from event
  if (!accumulator.metadata) {
    const eventMeta = extractMessageMetadataFromEvent(data);
    if (eventMeta) {
      accumulator.metadata = eventMeta;
      result.metadata = eventMeta;
    }
  }

  // ------- Top-level widget field -------
  if (data.widget && validateWidgetDefinition(data.widget)) {
    accumulator.currentWidget = data.widget;
    result.widgetFound = data.widget;
  }

  // ------- Widget side effects -------
  if (accumulator.currentWidget) {
    result.sideEffects.push({
      type: 'save_widget',
      payload: accumulator.currentWidget,
    });
    result.sideEffects.push({
      type: 'focus_widget',
      payload: accumulator.currentWidget,
    });
  }

  // ------- Custom events (tool traces) -------
  if (data.custom_event && typeof data.custom_event === 'object') {
    const customEvent = data.custom_event as Record<string, unknown>;
    if (customEvent.type === 'tool_call') {
      accumulator.currentTraces.push({
        type: 'tool_use',
        toolName: customEvent.name as string,
        content: JSON.stringify(customEvent.input),
      });
    } else if (customEvent.type === 'tool_result') {
      accumulator.currentTraces.push({
        type: 'tool_output',
        toolName: customEvent.name as string,
        content: 'Completed',
      });
    }
  }

  // ------- Status trace -------
  if (typeof data.status === 'string') {
    accumulator.currentTraces.push({
      type: 'thinking',
      content: data.status,
    });
  }

  // ------- Text accumulation -------
  if (newText) {
    accumulator.agentText += newText;
    result.textDelta = newText;
    result.fullText = accumulator.agentText;
  }

  // ------- Thinking state -------
  const hasContent = Boolean(
    accumulator.agentText || accumulator.currentWidget || accumulator.currentTraces.length > 0,
  );
  accumulator.isThinking = !hasContent;
  result.isThinking = !hasContent;

  // ------- Workspace activity -------
  result.sideEffects.push({
    type: 'workspace_activity',
    payload: {
      agentName: accumulator.agentName,
      text: accumulator.agentText || undefined,
      traces: [...accumulator.currentTraces],
    },
  });

  result.traces = [...accumulator.currentTraces];
  return result;
}
