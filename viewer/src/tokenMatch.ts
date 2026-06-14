import type { TokenLabel, TokenPrediction } from './types'

export type MatchStatus = 'correct' | 'mismatch' | 'not-applicable'

export function predictionMatchStatus(
  task: string | undefined,
  label: TokenLabel | null,
  pred: TokenPrediction | null,
): MatchStatus {
  if (pred == null || task !== 'grid_record_field') return 'not-applicable'

  if (label == null ||
      typeof pred.record !== 'number' ||
      typeof pred.field !== 'number' ||
      typeof label.record !== 'number' ||
      typeof label.field !== 'number') {
    return 'mismatch'
  }

  return pred.record === label.record && pred.field === label.field
    ? 'correct'
    : 'mismatch'
}
