import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

export default function Faq({ items }) {
  const [openIndex, setOpenIndex] = useState(0)

  return (
    <div className="divide-y divide-primary-100 border-t border-b border-primary-100">
      {items.map((item, i) => {
        const open = openIndex === i
        return (
          <div key={item.question}>
            <button
              type="button"
              onClick={() => setOpenIndex(open ? -1 : i)}
              aria-expanded={open}
              className="w-full flex items-center justify-between gap-4 py-5 text-left"
            >
              <span className="font-heading text-[15px] font-bold text-primary-900">{item.question}</span>
              <ChevronDown
                size={18}
                className={`shrink-0 text-primary-400 transition-transform duration-300 ${open ? 'rotate-180' : ''}`}
              />
            </button>
            <div
              className="grid transition-[grid-template-rows] duration-300 ease-out"
              style={{ gridTemplateRows: open ? '1fr' : '0fr' }}
            >
              <div className="overflow-hidden">
                <p className="text-sm text-primary-600 leading-relaxed pb-5 pr-8">{item.answer}</p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
