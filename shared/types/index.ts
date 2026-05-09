/**
 * 崩坏3专属AI陪伴助手 - 共享类型定义
 * 前后端共享的类型定义，确保类型安全
 */

// 基础类型
export interface BaseResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
  timestamp: string
}

export interface PaginationParams {
  page: number
  limit: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

export interface PaginatedResponse<T> extends BaseResponse<T[]> {
  pagination: {
    page: number
    limit: number
    total: number
    totalPages: number
    hasNext: boolean
    hasPrev: boolean
  }
}

// 游戏相关类型
export interface GameScene {
  id: string
  name: string
  description: string
  detectedAt: string
  confidence: number
  uiElements: string[]
  screenshot?: string // base64
}

export interface GameStatus {
  isRunning: boolean
  windowTitle: string
  scene?: GameScene
  lastUpdated: string
}

export interface GameAction {
  id: string
  name: string
  description: string
  hotkey?: string
  enabled: boolean
}

// 聊天相关类型
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  metadata?: {
    scene?: GameScene
    audioUrl?: string
    character?: string
    emotion?: string
  }
}

export interface ChatRequest {
  message: string
  scene?: GameScene
  character?: string
  useVoice?: boolean
  history?: ChatMessage[]
}

export interface ChatResponse {
  message: ChatMessage
  audioUrl?: string
  suggestedActions?: GameAction[]
  processingTime: number
}

// 音频相关类型
export interface AudioConfig {
  volume: number
  speed: number
  pitch: number
  characterVoice: string
}

export interface AudioRecording {
  id: string
  audioData: string // base64或Blob URL
  duration: number
  timestamp: string
  transcribedText?: string
}

// 视觉相关类型
export interface ScreenCapture {
  id: string
  imageData: string // base64
  timestamp: string
  detectedScenes: GameScene[]
  ocrText?: string[]
}

export interface OCRResult {
  text: string
  confidence: number
  boundingBox: [number, number, number, number] // [x1, y1, x2, y2]
}

// 角色相关类型
export interface Character {
  id: string
  name: string
  description: string
  voiceProfile: string
  personality: string
  enabled: boolean
}

export interface CharacterConfig {
  currentCharacter: string
  availableCharacters: Character[]
  voiceSettings: AudioConfig
}

// 知识库相关类型
export interface KnowledgeItem {
  id: string
  title: string
  content: string
  category: string
  tags: string[]
  relevance: number
  source?: string
  lastAccessed: string
}

export interface KnowledgeQuery {
  query: string
  category?: string
  limit?: number
  minRelevance?: number
}

// 记忆相关类型
export interface MemoryItem {
  id: string
  userId: string
  key: string
  value: any
  timestamp: string
  expiresAt?: string
  metadata?: Record<string, any>
}

export interface UserProfile {
  userId: string
  preferences: {
    language: string
    theme: 'light' | 'dark' | 'auto'
    notifications: boolean
    autoStart: boolean
  }
  gameStats: {
    totalPlayTime: number
    favoriteCharacter: string
    lastPlayed: string
    achievements: string[]
  }
  chatHistory: {
    totalMessages: number
    favoriteTopics: string[]
    lastActive: string
  }
}

// 设置相关类型
export interface AppSettings {
  general: {
    language: string
    theme: 'light' | 'dark' | 'auto'
    startMinimized: boolean
    autoUpdate: boolean
  }
  game: {
    autoDetect: boolean
    captureInterval: number
    hotkeys: Record<string, string>
    overlayEnabled: boolean
  }
  audio: {
    inputDevice: string
    outputDevice: string
    volume: number
    noiseReduction: boolean
  }
  ai: {
    model: string
    temperature: number
    maxTokens: number
    enableRAG: boolean
    enableMemory: boolean
  }
  advanced: {
    logLevel: 'debug' | 'info' | 'warn' | 'error'
    enableAnalytics: boolean
    enableErrorReporting: boolean
    developerMode: boolean
  }
}

// WebSocket消息类型
export type WebSocketMessageType = 
  | 'chat_message'
  | 'game_status'
  | 'audio_data'
  | 'screen_capture'
  | 'system_notification'
  | 'error'
  | 'ping'
  | 'pong'

export interface WebSocketMessage<T = any> {
  type: WebSocketMessageType
  data: T
  timestamp: string
  requestId?: string
}

// API响应类型
export interface APIEndpoints {
  // 聊天相关
  'POST /api/chat/send': {
    request: ChatRequest
    response: ChatResponse
  }
  'GET /api/chat/history': {
    request: PaginationParams & { character?: string }
    response: PaginatedResponse<ChatMessage>
  }
  
  // 游戏相关
  'GET /api/game/status': {
    request: {}
    response: GameStatus
  }
  'POST /api/game/capture': {
    request: {}
    response: ScreenCapture
  }
  
  // 音频相关
  'POST /api/audio/transcribe': {
    request: { audioData: string }
    response: { text: string }
  }
  'POST /api/audio/synthesize': {
    request: { text: string; character?: string }
    response: { audioUrl: string }
  }
  
  // 设置相关
  'GET /api/settings': {
    request: {}
    response: AppSettings
  }
  'PUT /api/settings': {
    request: Partial<AppSettings>
    response: AppSettings
  }
  
  // 健康检查
  'GET /api/health': {
    request: {}
    response: { status: string; timestamp: number }
  }
}

// 工具类型
export type Nullable<T> = T | null
export type Optional<T> = T | undefined
export type AsyncReturnType<T extends (...args: any) => Promise<any>> = 
  T extends (...args: any) => Promise<infer R> ? R : never

// 事件类型
export type AppEventType = 
  | 'game_detected'
  | 'game_lost'
  | 'scene_changed'
  | 'chat_message'
  | 'audio_playback_start'
  | 'audio_playback_end'
  | 'error_occurred'
  | 'settings_changed'

export interface AppEvent<T = any> {
  type: AppEventType
  data: T
  timestamp: string
}