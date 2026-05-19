import { describe, expect, it } from 'vitest'

import type { Analysis, Dataset, TransformationRead } from '../api'
import { renderSyntax } from '../syntaxRenderer'

function makeTx(
  overrides: Partial<TransformationRead> & {
    op_type: TransformationRead['op_type']
    op_args?: TransformationRead['op_args']
    position?: number
  },
): TransformationRead {
  return {
    id: 't-' + Math.random().toString(36).slice(2, 8),
    dataset_id: 'ds-1',
    position: overrides.position ?? 0,
    op_type: overrides.op_type,
    op_args: overrides.op_args ?? {},
    label: overrides.label ?? '',
    created_at: '2026-05-18T00:00:00Z',
  }
}

const DATASET: Pick<Dataset, 'filename'> = { filename: 'hip_outcomes.csv' }

describe('renderSyntax — pure function', () => {
  it('emits an import line for the dataset filename', () => {
    expect(renderSyntax(DATASET, [])).toBe('data <- import("hip_outcomes.csv")')
  })

  it('defaults filename when dataset is null', () => {
    expect(renderSyntax(null, [])).toBe('data <- import("dataset.csv")')
  })

  it('escapes double quotes in filenames', () => {
    const out = renderSyntax({ filename: 'a "b".csv' }, [])
    expect(out).toContain('"a \\"b\\".csv"')
  })

  it('renders filter ops with the given expression', () => {
    const tx = makeTx({ op_type: 'filter', op_args: { expr: '!is.na(hhs_6w)' } })
    expect(renderSyntax(DATASET, [tx])).toContain(
      'filter(data, !is.na(hhs_6w))',
    )
  })

  it('renders mutate ops with column and expression', () => {
    const tx = makeTx({
      op_type: 'mutate',
      op_args: { column: 'log_loss', expr: 'log(blood_loss_ml)' },
    })
    expect(renderSyntax(DATASET, [tx])).toContain(
      'mutate(data, log_loss = log(blood_loss_ml))',
    )
  })

  it('renders select / drop_na / log_transform / z_score / recode / group_summarise', () => {
    const txs = [
      makeTx({ op_type: 'select', op_args: { columns: ['a', 'b'] }, position: 0 }),
      makeTx({ op_type: 'drop_na', op_args: { columns: ['c'] }, position: 1 }),
      makeTx({ op_type: 'log_transform', op_args: { column: 'x' }, position: 2 }),
      makeTx({ op_type: 'z_score', op_args: { column: 'y' }, position: 3 }),
      makeTx({
        op_type: 'recode',
        op_args: { column: 'sex', mapping: { M: '1', F: '0' } },
        position: 4,
      }),
      makeTx({
        op_type: 'group_summarise',
        op_args: { group_by: ['g'], summarise: { mean_x: 'mean(x)' } },
        position: 5,
      }),
    ]
    const out = renderSyntax(DATASET, txs)
    expect(out).toContain('select(data, "a", "b")')
    expect(out).toContain('drop_na(data, "c")')
    expect(out).toContain('mutate(data, log_x = log(x))')
    expect(out).toContain('mutate(data, z_y = scale(y))')
    expect(out).toContain('recode(data, sex,')
    expect(out).toContain('group_summarise(data, by =')
  })

  it('honours position order ascending', () => {
    const txs = [
      makeTx({ op_type: 'filter', op_args: { expr: 'second' }, position: 1 }),
      makeTx({ op_type: 'filter', op_args: { expr: 'first' }, position: 0 }),
    ]
    const lines = renderSyntax(DATASET, txs).split('\n')
    // line[0] = import; line[1] should be 'first'; line[2] should be 'second'.
    expect(lines[1]).toContain('first')
    expect(lines[2]).toContain('second')
  })

  it('emits result <- ttest(...) for an independent_t analysis with a formula', () => {
    const analysis: Analysis = {
      id: 'a-1',
      project_id: 'p-1',
      dataset_id: 'ds-1',
      question_type: 'group_comparison',
      chosen_test: 'independent_t',
      recommendation_rationale: '',
      variables: { outcome: 'hhs_6w', groups: 'approach' },
      status: 'completed',
      created_at: '2026-05-18T00:00:00Z',
      result: null,
    }
    const out = renderSyntax(DATASET, [], [analysis])
    expect(out).toContain('result <- ttest(data, formula = hhs_6w ~ approach)')
  })

  it('numbers subsequent analyses result_2, result_3, …', () => {
    const base = {
      id: 'a',
      project_id: 'p-1',
      dataset_id: 'ds-1',
      question_type: 'group_comparison' as const,
      recommendation_rationale: '',
      status: 'completed' as const,
      created_at: '2026-05-18T00:00:00Z',
      result: null,
    }
    const out = renderSyntax(DATASET, [], [
      {
        ...base,
        id: 'a1',
        chosen_test: 'independent_t',
        variables: { outcome: 'y', groups: 'g' },
      },
      {
        ...base,
        id: 'a2',
        chosen_test: 'pearson',
        variables: { outcome: 'y', groups: 'x' },
      },
    ])
    expect(out).toContain('result <- ttest')
    expect(out).toContain('result_2 <- cor.test')
  })
})
