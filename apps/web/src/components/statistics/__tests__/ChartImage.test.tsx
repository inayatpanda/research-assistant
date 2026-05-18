import { cleanup, fireEvent, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ChartImage } from '../ChartImage'

const PNG_DATA_URI =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABcuP+EgAAAABJRU5ErkJggg=='

afterEach(() => cleanup())

describe('ChartImage', () => {
  it('renders nothing when chart is null', () => {
    const { container } = render(<ChartImage chart={null} alt="x" />)
    expect(container.firstChild).toBeNull()
  })

  it('renders thumbnail when chart is present', () => {
    const { getAllByAltText, container } = render(
      <ChartImage
        chart={{ format: 'png', data_uri: PNG_DATA_URI, byte_size: 70 }}
        alt="My chart"
      />
    )
    const imgs = getAllByAltText('My chart') as HTMLImageElement[]
    expect(imgs.length).toBeGreaterThanOrEqual(1)
    expect(imgs[0].src).toBe(PNG_DATA_URI)
    expect(container.querySelector('button')).not.toBeNull()
  })

  it('opens zoom modal on thumbnail click and shows full-size image', () => {
    const { getByLabelText, getAllByAltText } = render(
      <ChartImage
        chart={{ format: 'png', data_uri: PNG_DATA_URI, byte_size: 70 }}
        alt="Plot"
      />
    )
    // Modal is portal-rendered; initially only the thumbnail exists.
    const trigger = getByLabelText('View Plot full size')
    fireEvent.click(trigger)
    // After click, the dialog opens and a second <img alt="Plot"> appears.
    const imgs = getAllByAltText('Plot') as HTMLImageElement[]
    expect(imgs.length).toBeGreaterThanOrEqual(2)
  })

  it('download link href is the data URI', () => {
    const { getByLabelText, getByRole } = render(
      <ChartImage
        chart={{ format: 'png', data_uri: PNG_DATA_URI, byte_size: 70 }}
        alt="Plot"
        downloadName="my-plot"
      />
    )
    fireEvent.click(getByLabelText('View Plot full size'))
    const link = getByRole('link', { name: /download png/i }) as HTMLAnchorElement
    expect(link.getAttribute('href')).toBe(PNG_DATA_URI)
    expect(link.getAttribute('download')).toBe('my-plot.png')
  })
})
