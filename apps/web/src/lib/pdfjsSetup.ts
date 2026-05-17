// Configure pdfjs-dist worker for react-pdf. Must be imported before any <Document>.
// Vite resolves the `?url` suffix to a static asset URL.
import workerSrc from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { pdfjs } from 'react-pdf'

pdfjs.GlobalWorkerOptions.workerSrc = workerSrc
