import type { IconProps } from '@phosphor-icons/react'
import {
  ArrowCounterClockwise,
  Bell,
  ChatCircle,
  ClockCounterClockwise,
  Code,
  Copy,
  DotsThree,
  DotsThreeVertical,
  DownloadSimple,
  FileText,
  Files,
  Link as LinkIconPh,
  Microphone,
  Paperclip,
  PencilSimple,
  Plus,
  PushPin,
  Smiley,
  SpeakerHigh,
  SpeakerSlash,
  Star,
  Trash,
  X,
} from '@phosphor-icons/react'

/** Единый вес иконок портала — Phosphor Light. */
export const PORTAL_ICON_WEIGHT = 'light' as const

export const PORTAL_ICON_SIZE = 20
export const PORTAL_ICON_SIZE_SM = 16
export const PORTAL_ICON_SIZE_MENU = 18

type BaseProps = Omit<IconProps, 'weight'>

function withDefaults(size: number, props: BaseProps) {
  return { size, weight: PORTAL_ICON_WEIGHT, 'aria-hidden': true as const, ...props }
}

export function IconBell(props: BaseProps) {
  return <Bell {...withDefaults(PORTAL_ICON_SIZE, props)} />
}

export function IconSpeakerOn(props: BaseProps) {
  return <SpeakerHigh {...withDefaults(PORTAL_ICON_SIZE_SM, props)} />
}

export function IconSpeakerOff(props: BaseProps) {
  return <SpeakerSlash {...withDefaults(PORTAL_ICON_SIZE_SM, props)} />
}

export function IconPencil(props: BaseProps) {
  return <PencilSimple {...withDefaults(PORTAL_ICON_SIZE_SM, props)} />
}

export function IconTrash(props: BaseProps) {
  return <Trash {...withDefaults(PORTAL_ICON_SIZE_SM, props)} />
}

export function IconX(props: BaseProps) {
  return <X {...withDefaults(PORTAL_ICON_SIZE_SM, props)} />
}

export function IconReset(props: BaseProps) {
  return <ArrowCounterClockwise {...withDefaults(PORTAL_ICON_SIZE_SM, props)} />
}

export function IconDotsThree(props: BaseProps) {
  return <DotsThree {...withDefaults(PORTAL_ICON_SIZE_SM, props)} />
}

export function IconDotsThreeVertical(props: BaseProps) {
  return <DotsThreeVertical {...withDefaults(PORTAL_ICON_SIZE_SM, props)} />
}

export function IconChat(props: BaseProps) {
  return <ChatCircle {...withDefaults(PORTAL_ICON_SIZE, props)} />
}

export function IconFileText(props: BaseProps) {
  return <FileText {...withDefaults(PORTAL_ICON_SIZE_SM, props)} />
}

export function IconStar(props: BaseProps & { filled?: boolean }) {
  const { filled, ...rest } = props
  return (
    <Star
      {...withDefaults(PORTAL_ICON_SIZE, rest)}
      weight={filled ? 'fill' : PORTAL_ICON_WEIGHT}
    />
  )
}

export function IconHistory(props: BaseProps) {
  return <ClockCounterClockwise {...withDefaults(PORTAL_ICON_SIZE_MENU, props)} />
}

export function IconCopy(props: BaseProps) {
  return <Copy {...withDefaults(PORTAL_ICON_SIZE_MENU, props)} />
}

export function IconDownload(props: BaseProps) {
  return <DownloadSimple {...withDefaults(PORTAL_ICON_SIZE_SM, props)} />
}

export function IconLink(props: BaseProps) {
  return <LinkIconPh {...withDefaults(PORTAL_ICON_SIZE_MENU, props)} />
}

export function IconCode(props: BaseProps) {
  return <Code {...withDefaults(PORTAL_ICON_SIZE_MENU, props)} />
}

export function IconFiles(props: BaseProps) {
  return <Files {...withDefaults(PORTAL_ICON_SIZE_MENU, props)} />
}

export function IconTrashMenu(props: BaseProps) {
  return <Trash {...withDefaults(PORTAL_ICON_SIZE_MENU, props)} />
}

export function IconStarMenu(props: BaseProps & { filled?: boolean }) {
  const { filled, ...rest } = props
  return (
    <Star
      {...withDefaults(PORTAL_ICON_SIZE_MENU, rest)}
      weight={filled ? 'fill' : PORTAL_ICON_WEIGHT}
    />
  )
}

export function IconPlus(props: BaseProps) {
  return <Plus {...withDefaults(PORTAL_ICON_SIZE_SM, props)} />
}

export function IconDocRowPlus(props: BaseProps) {
  return <Plus {...withDefaults(PORTAL_ICON_SIZE, props)} />
}

export function IconDocRowChat(props: BaseProps) {
  return <ChatCircle {...withDefaults(PORTAL_ICON_SIZE, props)} />
}

export function IconPaperclip(props: BaseProps) {
  return <Paperclip {...withDefaults(PORTAL_ICON_SIZE, props)} />
}

export function IconMicrophone(props: BaseProps) {
  return <Microphone {...withDefaults(PORTAL_ICON_SIZE, props)} />
}

export function IconSmiley(props: BaseProps) {
  return <Smiley {...withDefaults(PORTAL_ICON_SIZE, props)} />
}

export function IconPin(props: BaseProps) {
  return <PushPin {...withDefaults(PORTAL_ICON_SIZE_SM, props)} />
}
