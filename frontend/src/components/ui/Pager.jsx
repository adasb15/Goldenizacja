function Pager({ page, onPrev, onNext }) {
  const from = page.total === 0 ? 0 : page.offset + 1
  const to = Math.min(page.offset + page.limit, page.total)
  const canPrev = page.offset > 0
  const canNext = page.offset + page.limit < page.total

  return (
    <div className="pager">
      <span className="pager__meta">
        {from}-{to} z {page.total}
      </span>

      <div className="pager__actions">
        <button type="button" className="button button--secondary" onClick={onPrev} disabled={!canPrev}>
          Poprzednia
        </button>
        <button type="button" className="button button--secondary" onClick={onNext} disabled={!canNext}>
          Nastepna
        </button>
      </div>
    </div>
  )
}

export { Pager }
