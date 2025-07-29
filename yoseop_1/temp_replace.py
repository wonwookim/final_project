#!/usr/bin/env python3

# Read the file
with open('llm/candidate/model.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all LLMProvider references with string equivalents
replacements = [
    ('LLMProvider.OPENAI_GPT4O_MINI', '"openai_gpt4o_mini"'),
    ('LLMProvider.OPENAI_GPT4', '"openai_gpt4"'),
    ('LLMProvider.OPENAI_GPT35', '"openai_gpt35"'),
    ('LLMResponse', 'SimpleLLMResponse'),
    (': LLMProvider', ': str'),
    ('List[LLMProvider]', 'List[str]'),
    ('Dict[LLMProvider,', 'Dict[str,'),
]

for old, new in replacements:
    content = content.replace(old, new)

# Write back
with open('llm/candidate/model.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Replacements completed')
