"use client";

import { useEffect, useRef, useState } from "react";

export type MultiSelectOption = {
  value: string;
  label: string;
};

type Props = {
  label: string;
  options: MultiSelectOption[];
  values: string[];
  onChange: (values: string[]) => void;
};

export function MultiSelect({ label, options, values, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const selectedLabels = options
    .filter((option) => values.includes(option.value))
    .map((option) => option.label);

  const toggle = (value: string) => {
    if (value === "any") {
      onChange(values.includes("any") ? [] : ["any"]);
      return;
    }
    if (values.includes(value)) {
      onChange(values.filter((current) => current !== value));
    } else {
      onChange([...values.filter((current) => current !== "any"), value]);
    }
  };

  return (
    <div className="multi-select" ref={rootRef}>
      <button
        type="button"
        className="multi-select-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <span>
          {selectedLabels.length ? selectedLabels.join(", ") : `Select ${label}`}
        </span>
        <span aria-hidden="true">⌄</span>
      </button>
      {open && (
        <div className="multi-select-menu" role="listbox" aria-label={label}>
          {options.map((option) => (
            <label key={option.value} className="multi-select-option">
              <input
                type="checkbox"
                checked={values.includes(option.value)}
                onChange={() => toggle(option.value)}
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
