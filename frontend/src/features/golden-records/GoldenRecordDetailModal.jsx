import { useEffect, useState } from 'react'

import { getChangeHistory, getLineage } from '../../api/serving'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { formatDate, formatDateTime, formatValue } from '../../utils/formatters'

const PERSON_FIELDS = [
  ['PESEL', 'pesel'],
  ['Numer dowodu', 'serial_number_id_card'],
  ['Numer paszportu', 'serial_number_passport'],
  ['Imię', 'first_name'],
  ['Drugie imię', 'second_name'],
  ['Nazwisko', 'last_name'],
  ['Nazwisko rodowe', 'family_name'],
  ['Data urodzenia', 'birth_date', 'date'],
  ['Miejsce urodzenia', 'place_of_birth'],
  ['Płeć', 'sex', 'sex'],
  ['Obywatelstwo', 'citizenship'],
  ['Telefon', 'phone_number'],
  ['E-mail', 'email_address'],
  ['Utworzono', 'created_at', 'datetime'],
  ['Zaktualizowano', 'updated_at', 'datetime'],
]

const PARTY_FIELDS = [
  ['Nazwa', 'name'],
  ['Nazwa skrócona', 'short_name'],
  ['Typ podmiotu', 'legal_entity_type'],
  ['Kraj rejestracji', 'registration_country'],
  ['Data założenia', 'establishment_date', 'date'],
  ['Utworzono', 'created_at', 'datetime'],
  ['Zaktualizowano', 'updated_at', 'datetime'],
]

const PERSON_IDENTIFIER_ROWS = [
  ['PESEL', 'pesel'],
  ['Numer dowodu', 'serial_number_id_card'],
  ['Numer paszportu', 'serial_number_passport'],
]

const ADDRESS_SOURCE_FIELDS = [
  ['Typ', 'address_type'],
  ['Ulica', 'street'],
  ['Nr budynku', 'building_number'],
  ['Nr lokalu', 'apartment_number'],
  ['Miasto', 'city'],
  ['Kod pocztowy', 'postal_code'],
  ['Kraj', 'country'],
  ['Od', 'valid_from', 'date'],
  ['Do', 'valid_to', 'date'],
]

const ATTRIBUTE_LABELS = {
  PESEL: 'PESEL',
  Serial_Number_ID_Card: 'Numer dowodu',
  Serial_Number_Passport: 'Numer paszportu',
  First_Name: 'Imię',
  Second_Name: 'Drugie imię',
  Last_Name: 'Nazwisko',
  Family_Name: 'Nazwisko rodowe',
  Birth_Date: 'Data urodzenia',
  Place_Of_Birth: 'Miejsce urodzenia',
  Sex: 'Płeć',
  Citizenship: 'Obywatelstwo',
  Phone_Number: 'Telefon',
  Email_Address: 'E-mail',
  Created_At: 'Utworzono',
  Updated_At: 'Zaktualizowano',
  Name: 'Nazwa',
  Short_Name: 'Nazwa skrócona',
  Legal_Entity_Type: 'Typ podmiotu',
  Registration_Country: 'Kraj rejestracji',
  Establishment_Date: 'Data założenia',
  Street: 'Ulica',
  Building_Number: 'Nr budynku',
  Apartment_Number: 'Nr lokalu',
  City: 'Miasto',
  Postal_City: 'Miejscowość pocztowa',
  Postal_Code: 'Kod pocztowy',
  District: 'Powiat',
  Province: 'Województwo',
  Country: 'Kraj',
}

const ENTITY_TYPE_LABELS = {
  PERSON: 'Osoba',
  PARTY: 'Podmiot',
}

function formatFieldValue(value, type) {
  if (type === 'datetime') {
    return formatDateTime(value)
  }

  if (type === 'date') {
    return formatDate(value)
  }

  if (type === 'sex') {
    if (value === true) {
      return 'M'
    }
    if (value === false) {
      return 'K'
    }
    return '-'
  }

  return formatValue(value)
}

function formatSource(provenance) {
  if (!provenance?.source_system_code) {
    return '-'
  }

  return provenance.source_record_id
    ? `${provenance.source_system_code} (${provenance.source_record_id})`
    : provenance.source_system_code
}

function formatAttributeName(value) {
  if (!value) {
    return '-'
  }

  return ATTRIBUTE_LABELS[value] || String(value)
}

function formatEntityType(value) {
  if (!value) {
    return '-'
  }

  return ENTITY_TYPE_LABELS[value] || String(value)
}

function DetailGrid({ rows, data }) {
  return (
    <div className="detail-grid">
      {rows.map(([label, key, type]) => (
        <div key={key} className="detail-card">
          <span>{label}</span>
          <strong>{formatFieldValue(data?.[key], type)}</strong>
        </div>
      ))}
    </div>
  )
}

function PersonIdentifierTable({ data }) {
  return (
    <div className="table-wrap detail-table">
      <table>
        <thead>
          <tr>
            <th>Typ</th>
            <th>Wartość</th>
            <th>Źródło</th>
            <th>Reguła survivorship</th>
          </tr>
        </thead>
        <tbody>
          {PERSON_IDENTIFIER_ROWS.map(([label, key]) => (
            <tr key={key}>
              <td>{label}</td>
              <td>{formatValue(data?.[key])}</td>
              <td className="cell-break">{formatSource(data?.provenance?.[key])}</td>
              <td className="cell-nowrap">{data?.provenance?.[key]?.selection_rule || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function AddressTable({ addresses }) {
  if (!addresses || addresses.length === 0) {
    return <div className="banner">Brak adresów.</div>
  }

  return (
    <div className="table-wrap detail-table">
      <table>
        <thead>
          <tr>
            <th>Typ</th>
            <th>Ulica</th>
            <th>Nr budynku</th>
            <th>Nr lokalu</th>
            <th>Miasto</th>
            <th>Kod pocztowy</th>
            <th>Kraj</th>
            <th>Od</th>
            <th>Do</th>
          </tr>
        </thead>
        <tbody>
          {addresses.map((address) => (
            <tr key={`${address.address_id}-${address.address_type || 'address'}`}>
              <td>{formatValue(address.address_type)}</td>
              <td>{formatValue(address.street)}</td>
              <td>{formatValue(address.building_number)}</td>
              <td>{formatValue(address.apartment_number)}</td>
              <td>{formatValue(address.city)}</td>
              <td>{formatValue(address.postal_code)}</td>
              <td>{formatValue(address.country)}</td>
              <td>{formatDate(address.valid_from)}</td>
              <td>{formatDate(address.valid_to)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function AddressSourceTable({ addresses }) {
  const rows = (addresses || []).flatMap((address) =>
    ADDRESS_SOURCE_FIELDS.map(([label, key, type]) => ({
      addressId: address.address_id,
      addressType: address.address_type,
      label,
      value: formatFieldValue(address[key], type),
      provenance: address.provenance?.[key],
    })),
  )

  if (rows.length === 0) {
    return <div className="banner">Brak źródeł wartości adresów.</div>
  }

  return (
    <div className="table-wrap detail-table">
      <table>
        <thead>
          <tr>
            <th>Typ adresu</th>
            <th>Pole</th>
            <th>Wartość</th>
            <th>Źródło</th>
            <th>Reguła survivorship</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.addressId}-${row.label}`}>
              <td>{formatValue(row.addressType)}</td>
              <td>{row.label}</td>
              <td className="cell-break">{row.value}</td>
              <td className="cell-break">{formatSource(row.provenance)}</td>
              <td className="cell-nowrap">{row.provenance?.selection_rule || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function IdentityTable({ identities }) {
  if (!identities || identities.length === 0) {
    return <div className="banner">Brak identyfikatorów.</div>
  }

  return (
    <div className="table-wrap detail-table">
      <table>
        <thead>
          <tr>
            <th>Typ</th>
            <th>Wartość</th>
            <th>Poprawność</th>
            <th>Pewność dopasowania</th>
            <th>Od</th>
            <th>Do</th>
          </tr>
        </thead>
        <tbody>
          {identities.map((identity) => (
            <tr key={identity.party_identity_id}>
              <td>{identity.identity_type}</td>
              <td className="cell-break">{identity.identity_value}</td>
              <td>
                <StatusBadge
                  value={identity.is_valid === true ? 'POPRAWNY' : identity.is_valid === false ? 'BŁĘDNY' : 'BRAK'}
                />
              </td>
              <td>{formatValue(identity.match_confidence)}</td>
              <td>{formatDate(identity.valid_from)}</td>
              <td>{formatDate(identity.valid_to)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function LineageTab({ lineage }) {
  if (lineage.status === 'loading') {
    return <div className="banner">Ładowanie pochodzenia rekordu...</div>
  }

  if (lineage.status === 'error') {
    return <div className="banner banner--danger">Błąd pobierania pochodzenia rekordu: {lineage.error}</div>
  }

  const items = lineage.data?.items ?? []

  if (items.length === 0) {
    return <div className="banner">Brak wpisów pochodzenia dla tego rekordu.</div>
  }

  return (
    <div className="table-wrap detail-table">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Typ</th>
            <th>Atrybut</th>
            <th>System źródłowy</th>
            <th>ID rekordu źródłowego</th>
            <th>Partia importu</th>
            <th>Reguła selekcji</th>
            <th>Ocena zaufania</th>
            <th>Ocena jakości</th>
            <th>Status walidacji</th>
            <th>Zarejestrowano</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.lineage_id}>
              <td>{item.lineage_id}</td>
              <td>{formatEntityType(item.lineage_type)}</td>
              <td className="cell-break">{formatAttributeName(item.attribute_name)}</td>
              <td>{formatValue(item.source_system_code)}</td>
              <td className="cell-break">{formatValue(item.source_record_id)}</td>
              <td>{item.import_batch_id}</td>
              <td className="cell-nowrap">{formatValue(item.selection_rule)}</td>
              <td>{formatValue(item.trust_score)}</td>
              <td>{formatValue(item.quality_score)}</td>
              <td>{formatValue(item.validation_status)}</td>
              <td>{formatDateTime(item.recorded_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function HistoryTab({ history }) {
  if (history.status === 'loading') {
    return <div className="banner">Ładowanie historii zmian...</div>
  }

  if (history.status === 'error') {
    return <div className="banner banner--danger">Błąd pobierania historii zmian: {history.error}</div>
  }

  const items = history.data?.items ?? []

  if (items.length === 0) {
    return <div className="banner">Brak historii zmian dla tego rekordu.</div>
  }

  return (
    <div className="table-wrap detail-table">
      <table>
        <thead>
          <tr>
            <th>ID zmiany</th>
            <th>Typ encji</th>
            <th>Atrybut</th>
            <th>Stara wartość</th>
            <th>Nowa wartość</th>
            <th>Partia importu</th>
            <th>Data zmiany</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.change_id}>
              <td>{item.change_id}</td>
              <td>{formatEntityType(item.entity_type)}</td>
              <td className="cell-break">{formatAttributeName(item.attribute_name)}</td>
              <td className="cell-break">{formatValue(item.old_value)}</td>
              <td className="cell-break">{formatValue(item.new_value)}</td>
              <td>{formatValue(item.import_batch_id)}</td>
              <td>{formatDateTime(item.change_date)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function GoldenRecordDetailModal({ detail, onClose }) {
  const [activeTab, setActiveTab] = useState('details')
  const [lineage, setLineage] = useState({ status: 'loading', data: null, error: '' })
  const [history, setHistory] = useState({ status: 'loading', data: null, error: '' })

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    document.body.classList.add('modal-open')

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.classList.remove('modal-open')
    }
  }, [onClose])

  useEffect(() => {
    if (!detail.recordId || !detail.entityType) {
      return
    }

    let cancelled = false

    setLineage({ status: 'loading', data: null, error: '' })
    setHistory({ status: 'loading', data: null, error: '' })

    getLineage(detail.entityType, detail.recordId)
      .then((data) => {
        if (!cancelled) {
          setLineage({ status: 'success', data, error: '' })
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setLineage({ status: 'error', data: null, error: String(error.message || error) })
        }
      })

    getChangeHistory(detail.entityType, detail.recordId)
      .then((data) => {
        if (!cancelled) {
          setHistory({ status: 'success', data, error: '' })
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setHistory({ status: 'error', data: null, error: String(error.message || error) })
        }
      })

    return () => {
      cancelled = true
    }
  }, [detail.entityType, detail.recordId])

  const isPerson = detail.entityType === 'PERSON'
  const title = isPerson ? 'Szczegóły osoby' : 'Szczegóły podmiotu'
  const eyebrow = isPerson ? 'Szczegóły osoby' : 'Szczegóły podmiotu'
  const rows = isPerson ? PERSON_FIELDS : PARTY_FIELDS

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section className="comparison comparison-modal detail-modal" onClick={(event) => event.stopPropagation()}>
        <div className="comparison__header">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h2>{title}</h2>
          </div>

          <button type="button" className="modal-close" onClick={onClose} aria-label="Zamknij szczegóły" title="Zamknij">
            <svg className="modal-close__icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path d="M7 7L17 17" />
              <path d="M17 7L7 17" />
            </svg>
          </button>
        </div>

        <div className="segmented" style={{ margin: '0 0 1rem' }}>
          <button
            type="button"
            className={activeTab === 'details' ? 'segmented__item is-active' : 'segmented__item'}
            onClick={() => setActiveTab('details')}
          >
            Szczegóły
          </button>
          <button
            type="button"
            className={activeTab === 'lineage' ? 'segmented__item is-active' : 'segmented__item'}
            onClick={() => setActiveTab('lineage')}
          >
            Pochodzenie (lineage)
          </button>
          <button
            type="button"
            className={activeTab === 'history' ? 'segmented__item is-active' : 'segmented__item'}
            onClick={() => setActiveTab('history')}
          >
            Historia zmian
          </button>
        </div>

        {activeTab === 'details' ? (
          <>
            {detail.status === 'loading' ? <div className="banner">Ładowanie szczegółów...</div> : null}
            {detail.status === 'error' ? (
              <div className="banner banner--danger">Błąd pobierania szczegółów: {detail.error}</div>
            ) : null}

            {detail.data ? (
              <div className="detail-layout">
                <DetailGrid rows={rows} data={detail.data} />

                {isPerson ? (
                  <section className="detail-section">
                    <div className="section-header detail-section__header">
                      <div>
                        <p className="eyebrow">Identyfikatory</p>
                        <h3>Identyfikatory</h3>
                      </div>
                    </div>
                    <PersonIdentifierTable data={detail.data} />
                  </section>
                ) : null}

                {!isPerson ? (
                  <section className="detail-section">
                    <div className="section-header detail-section__header">
                      <div>
                        <p className="eyebrow">Identyfikatory</p>
                        <h3>Identyfikatory podmiotu</h3>
                      </div>
                    </div>
                    <IdentityTable identities={detail.data.identities} />
                  </section>
                ) : null}

                <section className="detail-section">
                  <div className="section-header detail-section__header">
                    <div>
                      <p className="eyebrow">Adresy</p>
                      <h3>Adresy</h3>
                    </div>
                  </div>
                  <AddressTable addresses={detail.data.addresses} />
                </section>

                <section className="detail-section">
                  <div className="section-header detail-section__header">
                    <div>
                      <p className="eyebrow">Źródła adresów</p>
                      <h3>Źródła wartości adresów</h3>
                    </div>
                  </div>
                  <AddressSourceTable addresses={detail.data.addresses} />
                </section>
              </div>
            ) : null}
          </>
        ) : null}

        {activeTab === 'lineage' ? <LineageTab lineage={lineage} /> : null}

        {activeTab === 'history' ? <HistoryTab history={history} /> : null}
      </section>
    </div>
  )
}

export { GoldenRecordDetailModal }
