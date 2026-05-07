export type ImportedTaskDraft = {
  prompt: string;
  model_ids: string[];
  category?: string;
};

type ParseTaskImportFileParams = {
  fileName: string;
  text: string;
  selectedModels: string[];
  category?: string;
};

function normalizePrompt(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const prompt = value.trim();
  return prompt ? prompt : null;
}

function normalizeModelIds(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .filter((item): item is string => typeof item === "string")
      .map((item) => item.trim())
      .filter(Boolean);
  }
  if (typeof value === "string") {
    return value
      .split(/[\s,，]+/)
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
}

function parseJsonl(text: string, category?: string): ImportedTaskDraft[] {
  const tasks: ImportedTaskDraft[] = [];
  const lines = text.split(/\r?\n/);
  for (let index = 0; index < lines.length; index += 1) {
    const rawLine = lines[index]?.trim();
    if (!rawLine) continue;
    let data: Record<string, unknown>;
    try {
      data = JSON.parse(rawLine) as Record<string, unknown>;
    } catch {
      throw new Error(`JSONL 第 ${index + 1} 行不是合法 JSON`);
    }
    const prompt = normalizePrompt(data.prompt) || normalizePrompt(data.user_prompt) || normalizePrompt(data.content);
    if (!prompt) {
      throw new Error(`JSONL 第 ${index + 1} 行缺少 prompt、user_prompt 或 content 字段`);
    }
    const modelIds = normalizeModelIds(data.model ?? data.models ?? data.model_ids);
    if (modelIds.length < 2) {
      throw new Error(`JSONL 第 ${index + 1} 行的 model 字段至少需要 2 个模型`);
    }
    const itemCategory = normalizePrompt(data.category) || category;
    tasks.push({ prompt, model_ids: modelIds, category: itemCategory || undefined });
  }
  if (!tasks.length) {
    throw new Error("JSONL 文件里没有可导入的任务");
  }
  return tasks;
}

function parseTxt(text: string, selectedModels: string[], category?: string): ImportedTaskDraft[] {
  if (selectedModels.length < 2) {
    throw new Error("TXT 导入前请先至少选择 2 个模型");
  }
  const tasks = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((prompt) => ({ prompt, model_ids: selectedModels, category: category || undefined }));
  if (!tasks.length) {
    throw new Error("TXT 文件里没有可导入的任务");
  }
  return tasks;
}

export function parseTaskImportFile({ fileName, text, selectedModels, category }: ParseTaskImportFileParams): ImportedTaskDraft[] {
  const lowerName = fileName.toLowerCase();
  if (lowerName.endsWith(".jsonl")) {
    return parseJsonl(text, category);
  }
  if (lowerName.endsWith(".txt")) {
    return parseTxt(text, selectedModels, category);
  }
  throw new Error("仅支持 .jsonl 或 .txt 文件");
}
