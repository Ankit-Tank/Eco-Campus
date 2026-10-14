import { useEffect, useMemo, useState } from 'react'
import { CalendarClock, ChevronDown, ChevronUp, Pencil, Plus, Power, Trash2, X } from 'lucide-react'
import ErrorState from '../../components/ui/ErrorState.jsx'
import Skeleton from '../../components/ui/Skeleton.jsx'
import { useApi } from '../../hooks/useApi.js'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import {
  createEquipment,
  createRoom,
  deleteEquipment,
  deleteRoom,
  getRooms,
  updateEquipment,
  updateRoom,
} from '../../services/roomsApi.js'
import { createTimetableEntry, deleteTimetableEntry, getTimetable, updateTimetableEntry } from '../../services/timetableApi.js'
import { getErrorMessage } from '../../utils/errors.js'
import { formatNumber } from '../../utils/format.js'

// Must match the values the backend accepts (backend/app/routes/rooms.py).
const ROOM_TYPES = ['classroom', 'lab', 'seminar', 'reading_room']
const EQUIPMENT_KINDS = ['light', 'fan', 'ac', 'projector', 'pc', 'lab_equipment']

const EMPTY_ROOM = { room_code: '', block: '', name: '', room_type: 'classroom', capacity: 40, idle_baseline_kw: 0.1 }
const EMPTY_EQUIPMENT = { kind: 'light', rated_kw: 0.04, count: 1, expected_in_class: 1 }
const EMPTY_CLASS = { day_of_week: 0, start_time: '09:00', end_time: '10:00', activity: 'Class', expected_students: 30 }

function Notice({ notice }) {
  if (!notice) return null
  return (
    <p className={notice.type === 'error' ? 'alert-note' : 'ok-note'} role={notice.type === 'error' ? 'alert' : 'status'}>
      {notice.text}
    </p>
  )
}

// Add / edit a room.
function RoomForm({ initial, onSave, onCancel, busy, isEdit }) {
  const { t } = useLanguage()
  const [v, setV] = useState(initial)
  const set = (name) => (e) => setV({ ...v, [name]: e.target.value })
  return (
    <form
      className="form inline-form"
      onSubmit={(e) => {
        e.preventDefault()
        onSave(v)
      }}
    >
      <div className="field">
        <label htmlFor="room-code">{t('rooms.code')}</label>
        <input id="room-code" value={v.room_code} onChange={set('room_code')} required minLength={2} maxLength={20} placeholder="A-101" />
      </div>
      <div className="field">
        <label htmlFor="room-block">{t('rooms.block')}</label>
        <input id="room-block" value={v.block} onChange={set('block')} required maxLength={10} placeholder="A" />
      </div>
      <div className="field field--wide">
        <label htmlFor="room-name">{t('rooms.name')}</label>
        <input id="room-name" value={v.name} onChange={set('name')} required minLength={2} maxLength={100} />
      </div>
      <div className="field">
        <label htmlFor="room-type">{t('rooms.type')}</label>
        <div className="select-field">
          <select id="room-type" value={v.room_type} onChange={set('room_type')}>
            {ROOM_TYPES.map((k) => (
              <option key={k} value={k}>
                {t(`rooms.types.${k}`)}
              </option>
            ))}
          </select>
          <ChevronDown size={16} aria-hidden="true" />
        </div>
      </div>
      <div className="field">
        <label htmlFor="room-cap">{t('rooms.capacity')}</label>
        <input id="room-cap" type="number" min="1" max="500" value={v.capacity} onChange={set('capacity')} required />
      </div>
      <div className="field">
        <label htmlFor="room-base">{t('rooms.baseline')}</label>
        <input id="room-base" type="number" step="0.01" min="0" value={v.idle_baseline_kw} onChange={set('idle_baseline_kw')} required />
      </div>
      <div className="inline-actions">
        <button type="submit" className="btn btn--primary btn--small" disabled={busy}>
          {t('rooms.save')}
        </button>
        {onCancel && (
          <button type="button" className="btn btn--outline btn--small" onClick={onCancel}>
            {t('rooms.cancel')}
          </button>
        )}
      </div>
      {isEdit && null}
    </form>
  )
}

// Equipment of one room + the weekly timetable.
function RoomDetail({ room, onChanged, report }) {
  const { t } = useLanguage()
  const [classes, setClasses] = useState(null)
  const [eq, setEq] = useState(EMPTY_EQUIPMENT)
  const [cls, setCls] = useState(EMPTY_CLASS)
  const [editingEq, setEditingEq] = useState(null) // { id, rated_kw, count, expected_in_class }
  const [editingClass, setEditingClass] = useState(null)
  const [busy, setBusy] = useState(false)

  async function loadClasses() {
    try {
      const res = await getTimetable({ room_id: room.id })
      setClasses(res.items || [])
    } catch (err) {
      report({ type: 'error', text: getErrorMessage(err, t) })
      setClasses([])
    }
  }
  useEffect(() => {
    loadClasses()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [room.id])

  async function run(action, after) {
    setBusy(true)
    try {
      await action()
      report({ type: 'success', text: t('rooms.saved') })
      await after()
    } catch (err) {
      report({ type: 'error', text: getErrorMessage(err, t) })
    } finally {
      setBusy(false)
    }
  }

  const sortedClasses = useMemo(
    () => [...(classes || [])].sort((a, b) => a.day_of_week - b.day_of_week || a.start_time.localeCompare(b.start_time)),
    [classes],
  )

  return (
    <div className="report-detail">
      {/* ---------------- equipment ---------------- */}
      <h3 className="report-detail-head">{t('rooms.equipment')}</h3>
      {room.equipment.length === 0 ? (
        <p className="note-text">{t('rooms.noEquipment')}</p>
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('rooms.kind')}</th>
                <th>{t('rooms.ratedKw')}</th>
                <th>{t('rooms.count')}</th>
                <th>{t('rooms.inClass')}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {room.equipment.map((e) =>
                editingEq?.id === e.id ? (
                  <tr key={e.id}>
                    <td>{t(`rooms.kinds.${e.kind}`)}</td>
                    <td>
                      <input aria-label={t('rooms.ratedKw')} type="number" step="0.001" min="0.001" style={{ width: 90 }} value={editingEq.rated_kw} onChange={(ev) => setEditingEq({ ...editingEq, rated_kw: ev.target.value })} />
                    </td>
                    <td>
                      <input aria-label={t('rooms.count')} type="number" min="1" style={{ width: 70 }} value={editingEq.count} onChange={(ev) => setEditingEq({ ...editingEq, count: ev.target.value })} />
                    </td>
                    <td>
                      <input aria-label={t('rooms.inClass')} type="number" step="0.1" min="0" max="1" style={{ width: 70 }} value={editingEq.expected_in_class} onChange={(ev) => setEditingEq({ ...editingEq, expected_in_class: ev.target.value })} />
                    </td>
                    <td>
                      <div className="inline-actions">
                        <button
                          type="button"
                          className="btn btn--primary btn--small"
                          disabled={busy}
                          onClick={() =>
                            run(
                              () =>
                                updateEquipment(e.id, {
                                  rated_kw: Number(editingEq.rated_kw),
                                  count: Number(editingEq.count),
                                  expected_in_class: Number(editingEq.expected_in_class),
                                }),
                              async () => {
                                setEditingEq(null)
                                onChanged()
                              },
                            )
                          }
                        >
                          {t('rooms.save')}
                        </button>
                        <button type="button" className="btn btn--outline btn--small" onClick={() => setEditingEq(null)}>
                          <X size={14} aria-label={t('rooms.cancel')} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  <tr key={e.id}>
                    <td>{t(`rooms.kinds.${e.kind}`)}</td>
                    <td>{formatNumber(e.rated_kw, 3)}</td>
                    <td>{e.count}</td>
                    <td>{formatNumber(e.expected_in_class, 2)}</td>
                    <td>
                      <div className="inline-actions">
                        <button type="button" className="btn btn--outline btn--small" onClick={() => setEditingEq({ id: e.id, rated_kw: e.rated_kw, count: e.count, expected_in_class: e.expected_in_class })} aria-label={`${t('rooms.edit')} ${t(`rooms.kinds.${e.kind}`)}`}>
                          <Pencil size={14} />
                        </button>
                        <button
                          type="button"
                          className="btn btn--danger btn--small"
                          disabled={busy}
                          aria-label={`${t('rooms.delete')} ${t(`rooms.kinds.${e.kind}`)}`}
                          onClick={() => window.confirm(t('rooms.confirmDelete')) && run(() => deleteEquipment(e.id), async () => onChanged())}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      )}

      <form
        className="form inline-form section-gap"
        onSubmit={(ev) => {
          ev.preventDefault()
          run(() => createEquipment(room.id, eq), async () => {
            setEq(EMPTY_EQUIPMENT)
            onChanged()
          })
        }}
      >
        <div className="field">
          <label htmlFor={`eq-kind-${room.id}`}>{t('rooms.kind')}</label>
          <div className="select-field">
            <select id={`eq-kind-${room.id}`} value={eq.kind} onChange={(ev) => setEq({ ...eq, kind: ev.target.value })}>
              {EQUIPMENT_KINDS.map((k) => (
                <option key={k} value={k}>
                  {t(`rooms.kinds.${k}`)}
                </option>
              ))}
            </select>
            <ChevronDown size={16} aria-hidden="true" />
          </div>
        </div>
        <div className="field">
          <label htmlFor={`eq-kw-${room.id}`}>{t('rooms.ratedKw')}</label>
          <input id={`eq-kw-${room.id}`} type="number" step="0.001" min="0.001" required value={eq.rated_kw} onChange={(ev) => setEq({ ...eq, rated_kw: ev.target.value })} />
        </div>
        <div className="field">
          <label htmlFor={`eq-count-${room.id}`}>{t('rooms.count')}</label>
          <input id={`eq-count-${room.id}`} type="number" min="1" required value={eq.count} onChange={(ev) => setEq({ ...eq, count: ev.target.value })} />
        </div>
        <div className="field">
          <label htmlFor={`eq-share-${room.id}`}>{t('rooms.inClass')}</label>
          <input id={`eq-share-${room.id}`} type="number" step="0.1" min="0" max="1" required value={eq.expected_in_class} onChange={(ev) => setEq({ ...eq, expected_in_class: ev.target.value })} />
        </div>
        <button type="submit" className="btn btn--outline btn--small" disabled={busy}>
          <Plus size={14} aria-hidden="true" /> {t('rooms.addEquipment')}
        </button>
      </form>

      {/* ---------------- timetable ---------------- */}
      <h3 className="report-detail-head section-gap">
        <CalendarClock size={16} aria-hidden="true" style={{ verticalAlign: '-3px' }} /> {t('rooms.timetable')}
      </h3>
      {classes === null ? (
        <Skeleton height={80} radius={10} />
      ) : sortedClasses.length === 0 ? (
        <p className="note-text">{t('rooms.noClasses')}</p>
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('rooms.day')}</th>
                <th>{t('rooms.start')}</th>
                <th>{t('rooms.end')}</th>
                <th>{t('rooms.activity')}</th>
                <th>{t('rooms.students')}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {sortedClasses.map((c) =>
                editingClass?.id === c.id ? (
                  <tr key={c.id}>
                    <td>{t('rooms.days')[c.day_of_week]}</td>
                    <td>
                      <input aria-label={t('rooms.start')} type="time" value={editingClass.start_time} onChange={(ev) => setEditingClass({ ...editingClass, start_time: ev.target.value })} />
                    </td>
                    <td>
                      <input aria-label={t('rooms.end')} type="time" value={editingClass.end_time} onChange={(ev) => setEditingClass({ ...editingClass, end_time: ev.target.value })} />
                    </td>
                    <td>
                      <input aria-label={t('rooms.activity')} value={editingClass.activity} maxLength={200} onChange={(ev) => setEditingClass({ ...editingClass, activity: ev.target.value })} />
                    </td>
                    <td>
                      <input aria-label={t('rooms.students')} type="number" min="0" style={{ width: 80 }} value={editingClass.expected_students} onChange={(ev) => setEditingClass({ ...editingClass, expected_students: ev.target.value })} />
                    </td>
                    <td>
                      <div className="inline-actions">
                        <button
                          type="button"
                          className="btn btn--primary btn--small"
                          disabled={busy}
                          onClick={() =>
                            run(
                              () =>
                                updateTimetableEntry(c.id, {
                                  start_time: editingClass.start_time,
                                  end_time: editingClass.end_time,
                                  activity: editingClass.activity,
                                  expected_students: Number(editingClass.expected_students),
                                }),
                              async () => {
                                setEditingClass(null)
                                await loadClasses()
                              },
                            )
                          }
                        >
                          {t('rooms.save')}
                        </button>
                        <button type="button" className="btn btn--outline btn--small" onClick={() => setEditingClass(null)}>
                          <X size={14} aria-label={t('rooms.cancel')} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  <tr key={c.id}>
                    <td>{t('rooms.days')[c.day_of_week]}</td>
                    <td>{c.start_time}</td>
                    <td>{c.end_time}</td>
                    <td>{c.activity}</td>
                    <td>{c.expected_students}</td>
                    <td>
                      <div className="inline-actions">
                        <button type="button" className="btn btn--outline btn--small" onClick={() => setEditingClass({ id: c.id, start_time: c.start_time, end_time: c.end_time, activity: c.activity, expected_students: c.expected_students })} aria-label={`${t('rooms.edit')} ${c.activity}`}>
                          <Pencil size={14} />
                        </button>
                        <button
                          type="button"
                          className="btn btn--danger btn--small"
                          disabled={busy}
                          aria-label={`${t('rooms.delete')} ${c.activity}`}
                          onClick={() => window.confirm(t('rooms.confirmDelete')) && run(() => deleteTimetableEntry(c.id), loadClasses)}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      )}

      <form
        className="form inline-form section-gap"
        onSubmit={(ev) => {
          ev.preventDefault()
          run(() => createTimetableEntry({ room_id: room.id, ...cls }), async () => {
            setCls({ ...EMPTY_CLASS, day_of_week: cls.day_of_week })
            await loadClasses()
          })
        }}
      >
        <div className="field">
          <label htmlFor={`cl-day-${room.id}`}>{t('rooms.day')}</label>
          <div className="select-field">
            <select id={`cl-day-${room.id}`} value={cls.day_of_week} onChange={(ev) => setCls({ ...cls, day_of_week: Number(ev.target.value) })}>
              {t('rooms.days').map((d, i) => (
                <option key={d} value={i}>
                  {d}
                </option>
              ))}
            </select>
            <ChevronDown size={16} aria-hidden="true" />
          </div>
        </div>
        <div className="field">
          <label htmlFor={`cl-start-${room.id}`}>{t('rooms.start')}</label>
          <input id={`cl-start-${room.id}`} type="time" required value={cls.start_time} onChange={(ev) => setCls({ ...cls, start_time: ev.target.value })} />
        </div>
        <div className="field">
          <label htmlFor={`cl-end-${room.id}`}>{t('rooms.end')}</label>
          <input id={`cl-end-${room.id}`} type="time" required value={cls.end_time} onChange={(ev) => setCls({ ...cls, end_time: ev.target.value })} />
        </div>
        <div className="field field--wide">
          <label htmlFor={`cl-act-${room.id}`}>{t('rooms.activity')}</label>
          <input id={`cl-act-${room.id}`} required maxLength={200} value={cls.activity} onChange={(ev) => setCls({ ...cls, activity: ev.target.value })} />
        </div>
        <div className="field">
          <label htmlFor={`cl-stu-${room.id}`}>{t('rooms.students')}</label>
          <input id={`cl-stu-${room.id}`} type="number" min="0" required value={cls.expected_students} onChange={(ev) => setCls({ ...cls, expected_students: ev.target.value })} />
        </div>
        <button type="submit" className="btn btn--outline btn--small" disabled={busy}>
          <Plus size={14} aria-hidden="true" /> {t('rooms.addClass')}
        </button>
      </form>
    </div>
  )
}

export default function AdminRooms() {
  const { t } = useLanguage()
  const [block, setBlock] = useState('all')
  const [openId, setOpenId] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [adding, setAdding] = useState(false)
  const [notice, setNotice] = useState(null)
  const [busy, setBusy] = useState(false)
  const { status, data, error, reload } = useApi(() => getRooms(), [])

  const rooms = data?.items || []
  const blocks = useMemo(() => [...new Set(rooms.map((r) => r.block))].sort(), [rooms])
  const shown = rooms.filter((r) => block === 'all' || r.block === block)

  async function save(action, after) {
    setBusy(true)
    setNotice(null)
    try {
      await action()
      setNotice({ type: 'success', text: t('rooms.saved') })
      await after?.()
      reload()
    } catch (err) {
      const text = err.status === 409 ? t('rooms.roomHasHistory') : getErrorMessage(err, t)
      setNotice({ type: 'error', text })
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <header className="page-head">
        <div>
          <h1>{t('rooms.title')}</h1>
          <p>{t('rooms.subtitle')}</p>
          <span className="sim-pill">{t('shell.simulated')}</span>
        </div>
        <div className="toolbar">
          <label className="select-pill">
            <span className="visually-hidden">{t('rooms.block')}</span>
            <select value={block} onChange={(e) => setBlock(e.target.value)}>
              <option value="all">{t('rooms.allBlocks')}</option>
              {blocks.map((b) => (
                <option key={b} value={b}>{`Block ${b}`}</option>
              ))}
            </select>
            <ChevronDown size={16} aria-hidden="true" />
          </label>
          <button type="button" className="btn btn--primary" onClick={() => setAdding(!adding)}>
            <Plus size={16} aria-hidden="true" /> {t('rooms.addRoom')}
          </button>
        </div>
      </header>

      <Notice notice={notice} />

      {adding && (
        <section className="card section-gap" style={{ marginBottom: 18 }}>
          <RoomForm
            initial={EMPTY_ROOM}
            busy={busy}
            onCancel={() => setAdding(false)}
            onSave={(v) =>
              save(
                () => createRoom(v),
                async () => setAdding(false),
              )
            }
          />
        </section>
      )}

      {status === 'error' && <ErrorState error={error} onRetry={reload} />}
      {status === 'loading' && !data && <Skeleton height={320} radius={14} />}

      {data && (
        <section className="card">
          {shown.length === 0 ? (
            <p className="empty-text">{t('rooms.empty')}</p>
          ) : (
            <ul className="report-list">
              {shown.map((r) => {
                const open = openId === r.id
                return (
                  <li key={r.id} className="report-item">
                    <div className="report-row">
                      <div className="report-text">
                        <strong>
                          {r.room_code} · {r.name}
                        </strong>
                        <span>
                          {`Block ${r.block}`} · {t(`rooms.types.${r.room_type}`)} · {t('rooms.capacity')}: {r.capacity} · {t('rooms.baseline')}: {formatNumber(r.idle_baseline_kw, 2)}
                        </span>
                      </div>
                      {!r.is_active && <span className="pill-muted">{t('rooms.activate')}?</span>}
                      <div className="inline-actions">
                        <button type="button" className="btn btn--outline btn--small" onClick={() => setEditingId(editingId === r.id ? null : r.id)} aria-label={`${t('rooms.edit')} ${r.room_code}`}>
                          <Pencil size={14} />
                        </button>
                        <button
                          type="button"
                          className="btn btn--outline btn--small"
                          disabled={busy}
                          aria-label={`${r.is_active ? t('rooms.deactivate') : t('rooms.activate')} ${r.room_code}`}
                          onClick={() => save(() => updateRoom(r.id, { is_active: !r.is_active }))}
                        >
                          <Power size={14} /> {r.is_active ? t('rooms.deactivate') : t('rooms.activate')}
                        </button>
                        <button
                          type="button"
                          className="btn btn--danger btn--small"
                          disabled={busy}
                          aria-label={`${t('rooms.delete')} ${r.room_code}`}
                          onClick={() => window.confirm(t('rooms.confirmDelete')) && save(() => deleteRoom(r.id))}
                        >
                          <Trash2 size={14} />
                        </button>
                        <button type="button" className="btn btn--outline btn--small" aria-expanded={open} onClick={() => setOpenId(open ? null : r.id)} aria-label={`${t('rooms.equipment')} / ${t('rooms.timetable')} ${r.room_code}`}>
                          {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>
                      </div>
                    </div>

                    {editingId === r.id && (
                      <div className="report-detail">
                        <RoomForm
                          isEdit
                          initial={{ room_code: r.room_code, block: r.block, name: r.name, room_type: r.room_type, capacity: r.capacity, idle_baseline_kw: r.idle_baseline_kw }}
                          busy={busy}
                          onCancel={() => setEditingId(null)}
                          onSave={(v) =>
                            save(
                              () => updateRoom(r.id, { ...v, capacity: Number(v.capacity), idle_baseline_kw: Number(v.idle_baseline_kw) }),
                              async () => setEditingId(null),
                            )
                          }
                        />
                      </div>
                    )}

                    {open && <RoomDetail room={r} onChanged={reload} report={setNotice} />}
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      )}
    </>
  )
}
