import { useState } from 'react'
import { X, MapPin } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Input } from '@/components/ui/input'

interface CityChipsProps {
  cities: string[]
  onChange: (cities: string[]) => void
  placeholder?: string
  max?: number
}

export function CityChips({
  cities,
  onChange,
  placeholder = 'Agregar ciudad...',
  max = 20,
}: CityChipsProps) {
  const [inputValue, setInputValue] = useState('')

  const addCities = (raw: string) => {
    const newCities = raw
      .split(/[,\n;]+/)
      .map((c) => c.trim())
      .filter(Boolean)

    if (newCities.length === 0) return

    const merged = [...cities]
    for (const city of newCities) {
      if (!merged.includes(city) && merged.length < max) {
        merged.push(city)
      }
    }
    onChange(merged)
    setInputValue('')
  }

  const removeCity = (city: string) => {
    onChange(cities.filter((c) => c !== city))
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      if (inputValue.trim()) addCities(inputValue)
    }
    if (e.key === 'Backspace' && !inputValue && cities.length > 0) {
      removeCity(cities[cities.length - 1])
    }
  }

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const pasted = e.clipboardData.getData('text')
    if (/[,\n;]/.test(pasted)) {
      e.preventDefault()
      addCities(inputValue + pasted)
    }
  }

  return (
    <div className="space-y-2">
      <div className="relative">
        <div className="flex items-center gap-1.5 flex-wrap min-h-[42px] p-2 rounded-lg border border-input bg-background focus-within:ring-1 focus-within:ring-ring">
          {cities.map((city) => (
            <span
              key={city}
              className="inline-flex items-center gap-1 rounded border border-primary/20 bg-primary/10 py-1 pl-2 pr-1.5 text-xs font-medium text-primary"
            >
              <MapPin className="w-2.5 h-2.5 opacity-60" />
              {city}
              <button
                type="button"
                onClick={() => removeCity(city)}
                className="ml-0.5 rounded p-1 transition-colors hover:bg-primary/20 focus-ring"
              >
                <X className="w-2.5 h-2.5" />
              </button>
            </span>
          ))}
          {cities.length < max && (
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              placeholder={cities.length === 0 ? placeholder : ''}
              className="flex-1 min-w-[120px] bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          )}
        </div>
      </div>
      <p className="text-[10px] text-muted-foreground">
        {cities.length}/{max} ciudades · Enter o coma para agregar
      </p>
    </div>
  )
}
