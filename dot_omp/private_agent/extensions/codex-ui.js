import { highlightCode } from "@oh-my-pi/pi-tui/theme";
import { plainText, styledSpans } from "@oh-my-pi/pi-tui/native/spans";

export default function (pi) {
  // shortcut: expanded details use stock cards; removing their frames needs a host renderer change.
  pi.registerTranscriptPresenter(block => {
    if (block.type !== "toolCall") return undefined;
    if (block.toolName === "edit") return "full";

    const details = block.result?.details;
    const display = block.toolName === "read" && typeof details?.displayContent?.text === "string"
      ? details.displayContent : undefined;
    const output = (display?.text ?? (block.result?.content ?? [])
      .filter(part => part?.type === "text" && typeof part.text === "string")
      .map(part => part.text)
      .join("\n")).trimEnd();
    const meta = block.result?.details?.meta;
    const columns = meta?.limits?.columnTruncated;
    const inlineOnly = Boolean(meta?.truncation || meta?.minimized || meta?.artifactError || columns);
    const lines = output ? output.split(/\r\n|\r|\n/) : [];
    const preview = lines.slice(0, 3);
    const numbers = preview.map((_, index) => display?.lineNumbers
      ? display.lineNumbers[index] : display ? display.startLine + index : undefined);
    const numberWidth = Math.max(0, ...numbers.map(number => number == null ? 0 : String(number).length));
    const rows = preview.map((line, index) => [
      {
        t: `${index === 0 ? "└ " : "  "}${display ? `${String(numbers[index] ?? "").padStart(numberWidth)} ` : ""}`,
        s: "dim",
      },
      { t: line, s: "dim" },
    ]);
    if (lines.length > 3) {
      const remaining = lines.length - 3;
      rows.push([{
        t: `  + ${remaining} more ${inlineOnly ? "inline " : ""}${remaining === 1 ? "line" : "lines"} (Ctrl+O to expand)`,
        s: "dim",
      }]);
    }
    for (const [kind, info] of [["Truncated", meta?.truncation], ["Minimized", meta?.minimized], ["Column-truncated", columns]]) {
      if (!info) continue;
      const artifact = typeof info.artifactId === "string" ? ` · artifact://${info.artifactId}` : "";
      rows.push([{ t: `  ${kind} output${artifact}`, s: "warning" }]);
      if (info.artifactElidedBytes > 0) {
        rows.push([{ t: `  Saved artifact is incomplete: ${info.artifactElidedBytes} bytes omitted`, s: "warning" }]);
      }
    }
    const selectorBase = columns?.selectorBase
      || (columns?.artifactId != null && !columns.artifactElidedBytes ? `artifact://${columns.artifactId}` : undefined)
      || (meta?.source?.type === "path" ? meta.source.value : undefined);
    if (columns?.lines && selectorBase !== undefined) {
      const first = columns.lines.first;
      const cap = columns.rawByteCap === undefined ? "" : ` (byte cap: ${columns.rawByteCap})`;
      rows.push([{ t: `  Read ${selectorBase}:raw:${first}-${first}${cap}`, s: "warning" }]);
    }
    if (meta?.artifactError) {
      rows.push([{ t: `  Output artifact capture failed (${meta.artifactError}); complete output may be unavailable`, s: "warning" }]);
    }

    const exitCode = block.result?.details?.exitCode;
    const status = block.isError
      ? `Failed${typeof exitCode === "number" ? ` (exit ${exitCode})` : ""} `
      : block.result && !block.isPartial ? "Ran " : "Running ";

    const label = block.toolName === "bash" && typeof block.args?.command === "string"
      ? [
        { t: status, s: block.isError ? "error strong" : "toolTitle strong" },
        ...styledSpans(highlightCode(plainText(block.args.command), "bash").join("\n")),
      ]
      : undefined;
    return { compact: { label, rows } };
  });

  pi.registerComposerShape({
    label: "Codex",
    description: "Shaded prompt with no borders",
    style: {
      id: "local-codex",
      filledSurface: true,
      sideBorders: false,
      verticalChrome: 2,
      statusAttachment: "none",
      bottomBar: "full",
      bottomBarGap: false,
      defaultPromptGutter: "› ",
      defaultPaddingX: () => 0,
      sideChromeWidth: () => 0,
      renderTop: ({ width, surfaceColor }) => surfaceColor(" ".repeat(width)),
      renderRow: ({ gutter, text, pad, surfaceColor }) => [
        surfaceColor(gutter + text + pad),
      ],
      renderBottom: ({ width, surfaceColor }) => surfaceColor(" ".repeat(width)),
    },
  });
}
