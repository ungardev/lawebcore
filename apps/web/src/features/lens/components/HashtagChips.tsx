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
  const suggestionGroups = getSuggestionsForIndustry(industry);

  const addHashtag = (tag: string) => {
    const clean = tag.trim().toLowerCase().replace(/^#/, '').replace(/\s+/g, '');
    if (!clean || hashtags.includes(clean) || hashtags.length >= max) return;
    onChange([...hashtags, clean]);
    setInputValue('');
    setShowSuggestions(false);
  };

  const removeHashtag = (tag: string) => {
    onChange(hashtags.filter((h) => h !== tag));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      if (inputValue.trim()) addHashtag(inputValue);
    }
    if (e.key === 'Backspace' && !inputValue && hashtags.length > 0) {
      removeHashtag(hashtags[hashtags.length - 1]);
    }
  };

  const filteredSuggestions = getAllSuggestions(industry)
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
              className="inline-flex items-center gap-1 pl-2 pr-1.5 py-0.5 rounded-full bg-brand-purple/10 text-brand-purple text-xs font-medium border border-brand-purple/20"
            >
              <Hash className="w-2.5 h-2.5 opacity-60" />
              {tag}
              <button
                type="button"
                onClick={() => removeHashtag(tag)}
                className="ml-0.5 hover:bg-brand-purple/20 rounded-full p-0.5 transition-colors"
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
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
              placeholder={hashtags.length === 0 ? placeholder : '+'}
              className="flex-1 min-w-[100px] bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          )}
        </div>

        {showSuggestions && filteredSuggestions.length > 0 && (
          <div className="absolute z-10 mt-1 w-full rounded-lg border bg-popover shadow-md p-2 max-h-48 overflow-y-auto">
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
                    addHashtag(tag);
                  }}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-muted hover:bg-brand-purple/10 text-xs text-foreground transition-colors"
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
        {hashtags.length}/{max} hashtags · Enter o coma para agregar
      </p>
    </div>
  );
}
