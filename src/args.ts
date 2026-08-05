export function readFlag(args: string[], name: string): string | undefined {
  const index = args.indexOf(`--${name}`);
  return index >= 0 ? args[index + 1] : undefined;
}

export function hasFlag(args: string[], name: string): boolean {
  return args.includes(`--${name}`);
}

export function requiredFlag(args: string[], name: string): string {
  const value = readFlag(args, name);
  if (!value) throw new Error(`필수 옵션이 없습니다: --${name}`);
  return value;
}

