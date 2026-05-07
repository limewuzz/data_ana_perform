import { describe, expect, it } from "vitest";
import { parseTaskImportFile } from "@/lib/taskImport";

describe("parseTaskImportFile", () => {
  it("parses txt using selected models", () => {
    const tasks = parseTaskImportFile({
      fileName: "tasks.txt",
      text: "问题一\n\n问题二\n",
      selectedModels: ["kimi-k2.6", "mimo-v2.5-pro"],
      category: "general",
    });

    expect(tasks).toEqual([
      { prompt: "问题一", model_ids: ["kimi-k2.6", "mimo-v2.5-pro"], category: "general" },
      { prompt: "问题二", model_ids: ["kimi-k2.6", "mimo-v2.5-pro"], category: "general" },
    ]);
  });

  it("parses jsonl with prompt/user_prompt/content and model field", () => {
    const tasks = parseTaskImportFile({
      fileName: "tasks.jsonl",
      text: '{"prompt":"问题一","model":["kimi-k2.6","mimo-v2.5-pro"]}\n{"user_prompt":"问题二","model":"kimi-k2.6,mimo-v2.5-pro"}\n{"content":"问题三","model":"kimi-k2.6,mimo-v2.5-pro"}\n',
      selectedModels: [],
    });

    expect(tasks).toEqual([
      { prompt: "问题一", model_ids: ["kimi-k2.6", "mimo-v2.5-pro"], category: undefined },
      { prompt: "问题二", model_ids: ["kimi-k2.6", "mimo-v2.5-pro"], category: undefined },
      { prompt: "问题三", model_ids: ["kimi-k2.6", "mimo-v2.5-pro"], category: undefined },
    ]);
  });

  it("rejects jsonl without enough models", () => {
    expect(() =>
      parseTaskImportFile({
        fileName: "tasks.jsonl",
        text: '{"prompt":"问题一","model":"kimi-k2.6"}\n',
        selectedModels: [],
      }),
    ).toThrow("至少需要 2 个模型");
  });
});
