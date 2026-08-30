/**
 * Dangerpowers plugin for OpenCode.
 *
 * Registers this repository's skills/ and agents/ libraries into the live
 * config — no symlinks or manual config edits required.
 *
 * Install by adding to ~/.config/opencode/opencode.json:
 *   { "plugin": ["/path/to/dangerpowers/plugins/opencode-plugin.ts"] }
 */

import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { parse } from 'yaml';
import type { Config, Plugin } from '@opencode-ai/plugin';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const skillsDir = path.join(repoRoot, 'skills');
const agentsDir = path.join(repoRoot, 'agents');

const AGENT_CONFIG_KEYS = new Set([
  'description',
  'mode',
  'model',
  'variant',
  'temperature',
  'top_p',
  'steps',
  'color',
  'hidden',
  'disable',
  'options',
  'tools',
  'permission',
]);

type AgentFrontmatter = Record<string, unknown> & { name?: string };

type AgentConfig = { prompt: string } & Record<string, unknown>;

type DangerpowersConfig = Config & {
  skills?: { paths?: string[] };
};

const extractFrontmatter = (
  content: string,
): { frontmatter: AgentFrontmatter; body: string } => {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
  if (!match) return { frontmatter: {}, body: content };
  return { frontmatter: (parse(match[1]) as AgentFrontmatter) || {}, body: match[2] };
};

const loadAgents = (): Record<string, AgentConfig> => {
  const agents: Record<string, AgentConfig> = {};
  if (!fs.existsSync(agentsDir)) return agents;

  for (const file of fs.readdirSync(agentsDir)) {
    if (!file.endsWith('.md')) continue;
    const { frontmatter, body } = extractFrontmatter(
      fs.readFileSync(path.join(agentsDir, file), 'utf8'),
    );
    const name = frontmatter.name || path.basename(file, '.md');

    const agent: AgentConfig = { prompt: body.trim() };
    for (const [key, value] of Object.entries(frontmatter)) {
      if (key !== 'name' && AGENT_CONFIG_KEYS.has(key)) agent[key] = value;
    }
    agents[name] = agent;
  }
  return agents;
};

export const DangerpowersPlugin: Plugin = async ({ client }) => {
  const agents = loadAgents();

  await client.app.log({
    body: {
      service: 'dangerpowers',
      level: 'info',
      message: `dangerpowers loaded: ${Object.keys(agents).length} agents, skills from ${skillsDir}`,
    },
  });

  return {
    // Mutate the cached config singleton so skills/agents are discovered
    // without touching the user's config files.
    config: async (config: Config) => {
      const cfg = config as DangerpowersConfig;
      cfg.skills = cfg.skills || {};
      cfg.skills.paths = cfg.skills.paths || [];
      if (!cfg.skills.paths.includes(skillsDir)) {
        cfg.skills.paths.push(skillsDir);
      }

      config.agent = config.agent || {};
      for (const [name, agent] of Object.entries(agents)) {
        if (!config.agent[name]) config.agent[name] = agent;
      }
    },
  };
};

export default DangerpowersPlugin;
