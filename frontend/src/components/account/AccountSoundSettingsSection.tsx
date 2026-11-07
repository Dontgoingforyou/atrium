import { useCallback, useId, useState, type ChangeEvent } from 'react'

import { SOUND_PRESETS } from '../../domain/sound/soundPresets'
import {
  getChatDmSoundVolumePct,
  getNotificationSoundVolumePct,
  getResolvedChatDmSoundId,
  getResolvedNotificationSoundId,
  setChatDmSoundPresetId,
  setChatDmSoundVolumePct,
  setNotificationSoundPresetId,
  setNotificationSoundVolumePct,
} from '../../utils/notifications/soundChoiceStorage'
import { previewSoundSample } from '../../utils/notifications/notificationSound'
import { UI_SOUND_SKIP_VALUE } from '@/constants/uiSounds'
import { getUiSoundsEnabled, previewUiSound, setUiSoundsEnabled } from '@/utils/sound/uiSounds'
import shared from '@/styles/modules/account/AccountSettingsPage.module.css'
import styles from '@/styles/modules/account/AccountSoundSettingsSection.module.css'

export function AccountSoundSettingsSection() {
  const notificationVolId = useId()
  const chatVolId = useId()

  const [notificationPresetId, setNotificationPresetId] = useState(() =>
    getResolvedNotificationSoundId(),
  )
  const [chatPresetId, setChatPresetId] = useState(() => getResolvedChatDmSoundId())
  const [notificationVolPct, setNotificationVolPct] = useState(() => getNotificationSoundVolumePct())
  const [chatVolPct, setChatVolPct] = useState(() => getChatDmSoundVolumePct())
  const [uiSoundsOn, setUiSoundsOn] = useState(() => getUiSoundsEnabled())

  const onNotificationChange = useCallback((e: ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value
    setNotificationSoundPresetId(id)
    setNotificationPresetId(id)
  }, [])

  const onChatChange = useCallback((e: ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value
    setChatDmSoundPresetId(id)
    setChatPresetId(id)
  }, [])

  const onNotificationVolChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const v = Number(e.target.value)
    setNotificationSoundVolumePct(v)
    setNotificationVolPct(getNotificationSoundVolumePct())
  }, [])

  const onChatVolChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const v = Number(e.target.value)
    setChatDmSoundVolumePct(v)
    setChatVolPct(getChatDmSoundVolumePct())
  }, [])

  const previewNotification = useCallback(() => {
    const p = SOUND_PRESETS.find((x) => x.id === notificationPresetId)
    if (p) {
      void previewSoundSample(p.url, notificationVolPct / 100)
    }
  }, [notificationPresetId, notificationVolPct])

  const previewChat = useCallback(() => {
    const p = SOUND_PRESETS.find((x) => x.id === chatPresetId)
    if (p) {
      void previewSoundSample(p.url, chatVolPct / 100)
    }
  }, [chatPresetId, chatVolPct])

  const onUiSoundsToggle = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const next = e.target.checked
    setUiSoundsEnabled(next)
    setUiSoundsOn(next)
  }, [])

  const previewUiSounds = useCallback(() => {
    previewUiSound('success')
  }, [])

  return (
    <section className={shared.section} aria-labelledby="account-sound-heading">
      <h2 id="account-sound-heading" className="section-heading">
        Звук
      </h2>
      <p className={shared.lead}>
        Выберите сигнал для уведомлений портала и отдельно — для новых сообщений в личных чатах. Глобальное включение
        звука по-прежнему настраивается у значка колокольчика. Звуки интерфейса по умолчанию выключены; при каждом
        включении собирается новый набор из библиотеки procedural-sounds.
      </p>

      <div className={styles.soundControl} data-ui-sound={UI_SOUND_SKIP_VALUE}>
        <label className={shared.checkboxLabel}>
          <input type="checkbox" checked={uiSoundsOn} onChange={onUiSoundsToggle} />
          <span>Звуки интерфейса (клики и тосты)</span>
        </label>
        <div className={styles.controlRow}>
          <button
            type="button"
            className={`btn-secondary ${styles.previewBtn}`}
            onClick={previewUiSounds}
            data-ui-sound={UI_SOUND_SKIP_VALUE}
          >
            Прослушать
          </button>
        </div>
      </div>

      <div className={styles.soundControl}>
        <span className={styles.fieldLabel}>Звук уведомлений</span>
        <div className={styles.controlRow}>
          <select
            className={`form-input ${styles.soundSelect}`}
            value={notificationPresetId}
            onChange={onNotificationChange}
            aria-label="Звук уведомлений"
          >
            {SOUND_PRESETS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
          <button type="button" className={`btn-secondary ${styles.previewBtn}`} onClick={previewNotification}>
            Прослушать
          </button>
        </div>
      </div>

      <div className={styles.volumeBlock}>
        <label className={styles.volumeLabel} htmlFor={notificationVolId}>
          <span className={styles.fieldLabel}>Громкость уведомлений</span>
          <div className={styles.volumeRow}>
            <input
              id={notificationVolId}
              type="range"
              className={`form-input ${styles.range}`}
              min={0}
              max={100}
              step={1}
              value={notificationVolPct}
              onChange={onNotificationVolChange}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={notificationVolPct}
              aria-valuetext={`${notificationVolPct}%`}
            />
            <span className={`${styles.volumePct} text-muted`} aria-hidden>
              {notificationVolPct}%
            </span>
          </div>
        </label>
      </div>

      <div className={styles.soundControl}>
        <span className={styles.fieldLabel}>Звук сообщений в личных чатах</span>
        <div className={styles.controlRow}>
          <select
            className={`form-input ${styles.soundSelect}`}
            value={chatPresetId}
            onChange={onChatChange}
            aria-label="Звук сообщений в личных чатах"
          >
            {SOUND_PRESETS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
          <button type="button" className={`btn-secondary ${styles.previewBtn}`} onClick={previewChat}>
            Прослушать
          </button>
        </div>
      </div>

      <div className={styles.volumeBlock}>
        <label className={styles.volumeLabel} htmlFor={chatVolId}>
          <span className={styles.fieldLabel}>Громкость сообщений в личных чатах</span>
          <div className={styles.volumeRow}>
            <input
              id={chatVolId}
              type="range"
              className={`form-input ${styles.range}`}
              min={0}
              max={100}
              step={1}
              value={chatVolPct}
              onChange={onChatVolChange}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={chatVolPct}
              aria-valuetext={`${chatVolPct}%`}
            />
            <span className={`${styles.volumePct} text-muted`} aria-hidden>
              {chatVolPct}%
            </span>
          </div>
        </label>
      </div>
    </section>
  )
}
