<script setup lang="ts">
import { computed } from 'vue'
import { Marked } from 'marked'
import { markedHighlight } from 'marked-highlight'
import hljs from 'highlight.js'
import katex from 'katex'

const props = defineProps<{
  content: string
}>()

// Create marked instance with plugins
const marked = new Marked(
  markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code, lang) {
      const language = hljs.getLanguage(lang) ? lang : 'plaintext'
      return hljs.highlight(code, { language }).value
    }
  })
)

// Function to render LaTeX math
function renderMath(text: string): string {
  // Normalize double-escaped backslashes (\\cdot -> \cdot)
  // This handles cases where JSON serialization double-escaped backslashes
  const normalizeBackslashes = (math: string): string => {
    return math.replace(/\\\\([a-zA-Z]+)/g, '\\$1')
  }

  // Block math: $$...$$
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, math) => {
    try {
      const normalizedMath = normalizeBackslashes(math.trim())
      return katex.renderToString(normalizedMath, {
        displayMode: true,
        throwOnError: false,
        strict: false
      })
    } catch {
      return `<pre class="math-error">$$${math}$$</pre>`
    }
  })

  // Inline math: $...$  (but not $$)
  text = text.replace(/\$([^\$\n]+?)\$/g, (_, math) => {
    try {
      const normalizedMath = normalizeBackslashes(math.trim())
      return katex.renderToString(normalizedMath, {
        displayMode: false,
        throwOnError: false,
        strict: false
      })
    } catch {
      return `<code class="math-error">$${math}$</code>`
    }
  })

  return text
}

const renderedContent = computed(() => {
  if (!props.content) return ''

  // First render math, then markdown
  const withMath = renderMath(props.content)
  return marked.parse(withMath) as string
})
</script>

<template>
  <div class="solution-content" v-html="renderedContent"></div>
</template>

<style>
/* Highlight.js theme - adapted for Telegram */
.hljs {
  background: var(--tg-theme-secondary-bg-color) !important;
  color: var(--tg-theme-text-color);
}

.hljs-keyword,
.hljs-selector-tag,
.hljs-built_in,
.hljs-name,
.hljs-tag {
  color: #c678dd;
}

.hljs-string,
.hljs-title,
.hljs-section,
.hljs-attribute,
.hljs-literal,
.hljs-template-tag,
.hljs-template-variable,
.hljs-type,
.hljs-addition {
  color: #98c379;
}

.hljs-comment,
.hljs-quote,
.hljs-deletion,
.hljs-meta {
  color: #5c6370;
}

.hljs-number,
.hljs-regexp,
.hljs-selector-id,
.hljs-selector-class {
  color: #d19a66;
}

.hljs-attr,
.hljs-variable,
.hljs-template-variable,
.hljs-link,
.hljs-symbol,
.hljs-bullet {
  color: #61afef;
}

.math-error {
  color: #ff3b30;
  background: rgba(255, 59, 48, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
}
</style>
