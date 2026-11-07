import {
  EMOJI_PONG_BALL_RADIUS_RATIO,
  EMOJI_PONG_PADDLE_HEIGHT_RATIO,
  EMOJI_PONG_PADDLE_WIDTH_RATIO,
  EMOJI_PONG_PLAY_TOP_RATIO,
  EMOJI_PONG_SPEED_INITIAL,
  EMOJI_PONG_SPEED_MAX,
  EMOJI_PONG_SPEED_PER_POINT,
} from '@/utils/chat/emojiOnlyMessage'

export type BallState = { x: number; y: number; vx: number; vy: number }

export function currentSpeed(pointsPlayed: number): number {
  return Math.min(
    EMOJI_PONG_SPEED_MAX,
    EMOJI_PONG_SPEED_INITIAL + pointsPlayed * EMOJI_PONG_SPEED_PER_POINT,
  )
}

export function normalizeVelocity(
  vx: number,
  vy: number,
  speed: number,
): { vx: number; vy: number } {
  const len = Math.hypot(vx, vy) || 1
  return { vx: (vx / len) * speed, vy: (vy / len) * speed }
}

export function paddleYBottom(): number {
  return 1 - EMOJI_PONG_PADDLE_HEIGHT_RATIO * 2.2
}

export function paddleYTop(): number {
  return EMOJI_PONG_PLAY_TOP_RATIO + EMOJI_PONG_PADDLE_HEIGHT_RATIO * 1.2
}

export function hitPaddle(
  x: number,
  y: number,
  vy: number,
  paddleX: number,
  paddleY: number,
  goingDown: boolean,
): boolean {
  const ballR = EMOJI_PONG_BALL_RADIUS_RATIO
  const paddleW = EMOJI_PONG_PADDLE_WIDTH_RATIO
  const paddleH = EMOJI_PONG_PADDLE_HEIGHT_RATIO
  const left = paddleX - paddleW / 2
  const right = paddleX + paddleW / 2
  if (goingDown) {
    return (
      vy > 0
      && y + ballR >= paddleY
      && y - ballR <= paddleY + paddleH
      && x >= left
      && x <= right
    )
  }
  return (
    vy < 0
    && y - ballR <= paddleY + paddleH
    && y + ballR >= paddleY
    && x >= left
    && x <= right
  )
}

/** Отскок от нижней (fromBottom) или верхней ракетки. */
export function bounceOffPaddle(
  x: number,
  _y: number,
  px: number,
  fromBottom: boolean,
  pointsPlayed: number,
): BallState {
  const ballR = EMOJI_PONG_BALL_RADIUS_RATIO
  const paddleW = EMOJI_PONG_PADDLE_WIDTH_RATIO
  const hitOffset = (x - px) / (paddleW / 2)
  const nextSpeed = currentSpeed(pointsPlayed)
  const bottomY = paddleYBottom()
  const topY = paddleYTop()
  if (fromBottom) {
    const bounceAngle = -Math.PI / 2 + hitOffset * 0.85
    const vx = Math.cos(bounceAngle) * nextSpeed
    let vy = Math.sin(bounceAngle) * nextSpeed
    if (vy > -0.12) vy = -Math.abs(nextSpeed) * 0.85
    return { x, y: bottomY - ballR, vx, vy }
  }
  const bounceAngle = Math.PI / 2 + hitOffset * 0.85
  const vx = Math.cos(bounceAngle) * nextSpeed
  let vy = Math.sin(bounceAngle) * nextSpeed
  if (vy < 0.12) vy = Math.abs(nextSpeed) * 0.85
  return {
    x,
    y: topY + EMOJI_PONG_PADDLE_HEIGHT_RATIO + ballR,
    vx,
    vy,
  }
}

export function makeServe(towardBottom: boolean, pointsPlayed: number): BallState {
  const speed = currentSpeed(pointsPlayed)
  const angle = towardBottom
    ? Math.PI / 2 + (Math.random() * 0.5 - 0.25)
    : -Math.PI / 2 + (Math.random() * 0.5 - 0.25)
  const vx = Math.cos(angle) * speed * 0.35
  let vy = Math.sin(angle) * speed
  if (towardBottom && vy < 0) vy = Math.abs(vy)
  if (!towardBottom && vy > 0) vy = -Math.abs(vy)
  return { x: 0.5, y: 0.5, vx, vy }
}
