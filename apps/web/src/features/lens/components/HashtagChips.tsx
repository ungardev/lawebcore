import { useState } from 'react';
import { X, Plus, Hash } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import {
  getSuggestionsForIndustry,
  getAllSuggestions,
  type HashtagSuggestionGroup,
} from './HashtagSuggestions';

interface HashtagChipsProps {
  hashtags: string[];
  onChange: (hashtags: string[]) => void;
  industry?: string | null;
  placeholder?: string;
  max?: number;
}

export function HashtagChips({
  hashtags,
  onChange,
  industry,
  placeholder = "Agregar hashtag...",
  max = 30,
}: HashtagChipsProps) {
  const [inputValue, setInputValue] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const suggestionGroups = getSuggestionsForIndustry(industry ?? null);

  const addHashtags = (raw: string) => {
    const newTags = raw
      .split(/[,\n;]+/)
      .map((t) => t.trim().toLowerCase().replace(/^#/, '').replace(/\s+/g, ''))
      .filter(Boolean);

    if (newTags.length === 0) return;

    const merged = [...hashtags];
    for (const tag of newTags) {
      if (!merged.includes(tag) && merged.length < max) {
        merged.push(tag);
      }
    }
    onChange(merged);
    setInputValue('');
    setShowSuggestions(false);
  };

  const removeHashtag = (tag: string) => {
    onChange(hashtags.filter((h) => h !== tag));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      if (inputValue.trim()) addHashtags(inputValue);
    }
    if (e.key === 'Backspace' && !inputValue && hashtags.length > 0) {
      removeHashtag(hashtags[hashtags.length - 1]);
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const pasted = e.clipboardData.getData('text');
    if (/[,\n;]/.test(pasted)) {
      e.preventDefault();
      addHashtags(inputValue + pasted);
    }
  };

  const filteredSuggestions = getAllSuggestions(industry ?? null)
    .filter((s) => !hashtags.includes(s))
    .filter((s) => s.includes(inputValue.toLowerCase()))
    .slice(0, 12);

  return (
    <div className="space-y-2">
      <div className="relative">
        <div className="flex items-center gap-1.5 flex-wrap min-h-[42px] p-2 rounded-lg border border-input bg-background focus-within:ring-1 focus-within:ring-ring">
          {hashtags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 rounded border border-primary/20 bg-primary/10 py-1 pl-2 pr-1.5 text-xs font-medium text-primary"
            >
              <Hash className="w-2.5 h-2.5 opacity-60" />
              {tag}
              <button
                type="button"
                onClick={() => removeHashtag(tag)}
                className="ml-0.5 rounded p-1 transition-colors hover:bg-primary/20 focus-ring"
              >
                <X className="w-2.5 h-2.5" />
              </button>
            </span>
          ))}
          {hashtags.length < max && (
            <input
              type="text"
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value);
                setShowSuggestions(true);
              }}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
              placeholder={hashtags.length === 0 ? placeholder : '+'}
              className="flex-1 min-w-[100px] bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          )}
        </div>

        {showSuggestions && filteredSuggestions.length > 0 && (
          <div className="absolute z-10 mt-1 max-h-48 w-full overflow-y-auto rounded-md border border-divider bg-popover p-2 shadow-elevated">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5 font-semibold px-1">
              Sugerencias{industry ? ` · ${industry}` : ''}
            </p>
            <div className="flex flex-wrap gap-1">
              {filteredSuggestions.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    addHashtags(tag);
                  }}
                  className="inline-flex items-center gap-1 rounded border border-divider bg-surface-raised px-2 py-1 text-xs text-foreground transition-colors hover:border-primary/30 hover:bg-primary/10 focus-ring"
                >
                  <Hash className="w-2.5 h-2.5 opacity-50" />
                  {tag}
                  <Plus className="w-2.5 h-2.5 opacity-50" />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <p className="text-[10px] text-muted-foreground">
        {hashtags.length}/{max} hashtags · Enter, coma o pegar para agregar
      </p>
    </div>
  );
}
