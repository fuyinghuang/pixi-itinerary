import { useId } from "react";

const EXAMPLE =
  "10 days in South Africa for our anniversary — a few days in Cape Town, " +
  "some time in the winelands, then safari to finish.";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled: boolean;
}

export default function BriefForm({
  value,
  onChange,
  onSubmit,
  disabled,
}: Props) {
  const id = useId();

  return (
    <form
      className="brief"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <label htmlFor={id}>The client's brief, in their own words</label>
      <textarea
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="10 days in South Africa for our anniversary…"
        maxLength={2000}
        disabled={disabled}
      />
      <div className="brief-actions">
        <button type="submit" disabled={disabled || value.trim().length === 0}>
          Build itinerary
        </button>
        <button
          type="button"
          className="link"
          onClick={() => onChange(EXAMPLE)}
          disabled={disabled}
        >
          Use the example brief
        </button>
      </div>
    </form>
  );
}
