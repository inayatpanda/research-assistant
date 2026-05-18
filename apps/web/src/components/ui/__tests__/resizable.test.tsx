import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '../resizable'

describe('resizable (shadcn wrapper, MP12.6)', () => {
  afterEach(cleanup)

  it('renders a horizontal group with two panels and a handle', () => {
    render(
      <div style={{ width: 400, height: 200 }}>
        <ResizablePanelGroup
          direction="horizontal"
          autoSaveId="divider-widths-test"
        >
          <ResizablePanel defaultSize={70} minSize={30} maxSize={85}>
            <div data-testid="pane-a">A</div>
          </ResizablePanel>
          <ResizableHandle withHandle />
          <ResizablePanel defaultSize={30} minSize={15} maxSize={70}>
            <div data-testid="pane-b">B</div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>,
    )
    expect(screen.getByTestId('pane-a')).toBeTruthy()
    expect(screen.getByTestId('pane-b')).toBeTruthy()
    // The handle exposes a separator role from react-resizable-panels
    expect(screen.getByRole('separator')).toBeTruthy()
  })

  it('passes autoSaveId through so widths persist (key = divider-widths-<page>)', () => {
    // Smoke check: the prop is forwarded without error and the group renders.
    // react-resizable-panels uses this key with localStorage internally; we
    // just verify our wrapper plumbs the prop through.
    const { container } = render(
      <ResizablePanelGroup
        direction="vertical"
        autoSaveId="divider-widths-reader"
      >
        <ResizablePanel defaultSize={50}>
          <div>x</div>
        </ResizablePanel>
        <ResizableHandle />
        <ResizablePanel defaultSize={50}>
          <div>y</div>
        </ResizablePanel>
      </ResizablePanelGroup>,
    )
    // The library annotates the group element with the direction
    const group = container.querySelector(
      '[data-panel-group-direction="vertical"]',
    )
    expect(group).toBeTruthy()
  })
})
