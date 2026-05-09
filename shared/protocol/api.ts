/**
 * 崩坏3专属AI陪伴助手 - API协议定义
 * 前后端API接口规范，确保通信一致性
 */

import type { APIEndpoints } from '../types'

// API基础配置
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  WS_URL: import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/ws',
  TIMEOUT: 30000, // 30秒
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000, // 1秒
} as const

// API路径常量
export const API_PATHS = {
  // 聊天相关
  CHAT_SEND: '/api/chat/send',
  CHAT_HISTORY: '/api/chat/history',
  CHAT_STREAM: '/api/chat/stream',
  
  // 游戏相关
  GAME_STATUS: '/api/game/status',
  GAME_CAPTURE: '/api/game/capture',
  GAME_ACTIONS: '/api/game/actions',
  
  // 视觉相关
  VISION_DETECT: '/api/vision/detect',
  VISION_OCR: '/api/vision/ocr',
  
  // 音频相关
  AUDIO_TRANSCRIBE: '/api/audio/transcribe',
  AUDIO_SYNTHESIZE: '/api/audio/synthesize',
  AUDIO_RECORDINGS: '/api/audio/recordings',
  
  // 角色相关
  CHARACTERS_LIST: '/api/characters',
  CHARACTERS_SELECT: '/api/characters/select',
  CHARACTERS_VOICES: '/api/characters/voices',
  
  // 知识库相关
  KNOWLEDGE_QUERY: '/api/knowledge/query',
  KNOWLEDGE_ADD: '/api/knowledge/add',
  KNOWLEDGE_LIST: '/api/knowledge/list',
  
  // 记忆相关
  MEMORY_GET: '/api/memory/get',
  MEMORY_SET: '/api/memory/set',
  MEMORY_DELETE: '/api/memory/delete',
  MEMORY_SEARCH: '/api/memory/search',
  
  // 设置相关
  SETTINGS_GET: '/api/settings',
  SETTINGS_UPDATE: '/api/settings',
  SETTINGS_RESET: '/api/settings/reset',
  
  // 系统相关
  HEALTH_CHECK: '/api/health',
  SYSTEM_INFO: '/api/system/info',
  SYSTEM_LOGS: '/api/system/logs',
  
  // 文件相关
  FILES_UPLOAD: '/api/files/upload',
  FILES_DOWNLOAD: '/api/files/download',
  FILES_LIST: '/api/files/list',
} as const

// WebSocket事件类型
export const WS_EVENTS = {
  // 连接事件
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  ERROR: 'error',
  
  // 聊天事件
  CHAT_MESSAGE: 'chat_message',
  CHAT_RESPONSE: 'chat_response',
  CHAT_TYPING: 'chat_typing',
  
  // 游戏事件
  GAME_DETECTED: 'game_detected',
  GAME_LOST: 'game_lost',
  SCENE_CHANGED: 'scene_changed',
  SCREEN_CAPTURE: 'screen_capture',
  
  // 音频事件
  AUDIO_START: 'audio_start',
  AUDIO_DATA: 'audio_data',
  AUDIO_END: 'audio_end',
  AUDIO_TRANSCRIBED: 'audio_transcribed',
  
  // 系统事件
  SYSTEM_NOTIFICATION: 'system_notification',
  SYSTEM_WARNING: 'system_warning',
  SYSTEM_ERROR: 'system_error',
  SYSTEM_UPDATE: 'system_update',
  
  // 用户事件
  USER_ACTIVITY: 'user_activity',
  USER_SETTINGS_CHANGED: 'user_settings_changed',
  
  // 控制事件
  COMMAND_EXECUTE: 'command_execute',
  COMMAND_RESULT: 'command_result',
} as const

// API请求方法
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'

// API请求配置
export interface ApiRequestConfig {
  method?: HttpMethod
  headers?: Record<string, string>
  params?: Record<string, any>
  data?: any
  timeout?: number
  retry?: boolean
  signal?: AbortSignal
}

// API响应格式
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
  timestamp: string
  requestId?: string
}

// API错误类型
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: any
  ) {
    super(message)
    this.name = 'ApiError'
  }
  
  static fromResponse(response: ApiResponse): ApiError {
    return new ApiError(
      400, // 默认状态码
      response.error || 'unknown_error',
      response.message || '未知错误',
      response
    )
  }
}

// WebSocket连接配置
export interface WebSocketConfig {
  url: string
  protocols?: string[]
  reconnect?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
  heartbeatInterval?: number
}

// WebSocket消息包装器
export interface WebSocketMessage<T = any> {
  event: string
  data: T
  timestamp: string
  requestId?: string
  correlationId?: string
}

// API客户端接口
export interface ApiClient {
  // HTTP请求
  request<T extends keyof APIEndpoints>(
    endpoint: T,
    config?: ApiRequestConfig
  ): Promise<APIEndpoints[T]['response']>
  
  get<T extends keyof APIEndpoints>(
    endpoint: T,
    config?: Omit<ApiRequestConfig, 'method'>
  ): Promise<APIEndpoints[T]['response']>
  
  post<T extends keyof APIEndpoints>(
    endpoint: T,
    data?: APIEndpoints[T]['request'],
    config?: Omit<ApiRequestConfig, 'method' | 'data'>
  ): Promise<APIEndpoints[T]['response']>
  
  put<T extends keyof APIEndpoints>(
    endpoint: T,
    data?: APIEndpoints[T]['request'],
    config?: Omit<ApiRequestConfig, 'method' | 'data'>
  ): Promise<APIEndpoints[T]['response']>
  
  delete<T extends keyof APIEndpoints>(
    endpoint: T,
    config?: Omit<ApiRequestConfig, 'method'>
  ): Promise<APIEndpoints[T]['response']>
  
  // WebSocket
  connectWebSocket(config?: WebSocketConfig): Promise<WebSocket>
  disconnectWebSocket(): void
  sendWebSocketMessage<T>(message: WebSocketMessage<T>): boolean
  onWebSocketMessage<T>(event: string, callback: (data: T) => void): void
  offWebSocketMessage(event: string, callback: (data: any) => void): void
  
  // 工具方法
  setAuthToken(token: string): void
  clearAuthToken(): void
  setBaseUrl(url: string): void
}

// 请求拦截器
export type RequestInterceptor = (
  config: ApiRequestConfig
) => ApiRequestConfig | Promise<ApiRequestConfig>

// 响应拦截器
export type ResponseInterceptor = (
  response: Response,
  config: ApiRequestConfig
) => Response | Promise<Response>

// 错误拦截器
export type ErrorInterceptor = (
  error: Error,
  config: ApiRequestConfig
) => Error | Promise<Error>

// API客户端配置
export interface ApiClientConfig {
  baseUrl?: string
  wsUrl?: string
  timeout?: number
  defaultHeaders?: Record<string, string>
  interceptors?: {
    request?: RequestInterceptor[]
    response?: ResponseInterceptor[]
    error?: ErrorInterceptor[]
  }
  wsConfig?: WebSocketConfig
}

// 默认配置
export const DEFAULT_API_CONFIG: ApiClientConfig = {
  baseUrl: API_CONFIG.BASE_URL,
  wsUrl: API_CONFIG.WS_URL,
  timeout: API_CONFIG.TIMEOUT,
  defaultHeaders: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  wsConfig: {
    url: API_CONFIG.WS_URL,
    reconnect: true,
    reconnectInterval: 3000,
    maxReconnectAttempts: 5,
    heartbeatInterval: 30000,
  },
}

// 验证API响应
export function validateApiResponse<T>(response: any): response is ApiResponse<T> {
  return (
    response &&
    typeof response === 'object' &&
    'success' in response &&
    'timestamp' in response
  )
}

// 创建请求ID
export function createRequestId(): string {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

// 创建相关ID
export function createCorrelationId(): string {
  return `corr_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

// 延迟函数
export function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// 重试函数
export async function withRetry<T>(
  fn: () => Promise<T>,
  attempts: number = API_CONFIG.RETRY_ATTEMPTS,
  delayMs: number = API_CONFIG.RETRY_DELAY
): Promise<T> {
  let lastError: Error
  
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn()
    } catch (error) {
      lastError = error as Error
      
      if (i < attempts - 1) {
        await delay(delayMs * (i + 1)) // 指数退避
      }
    }
  }
  
  throw lastError
}

// API工具函数
export class ApiUtils {
  // 构建查询字符串
  static buildQueryString(params: Record<string, any>): string {
    const searchParams = new URLSearchParams()
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (Array.isArray(value)) {
          value.forEach(item => searchParams.append(key, String(item)))
        } else {
          searchParams.append(key, String(value))
        }
      }
    })
    
    const queryString = searchParams.toString()
    return queryString ? `?${queryString}` : ''
  }
  
  // 构建URL
  static buildUrl(baseUrl: string, path: string, params?: Record<string, any>): string {
    const url = new URL(path, baseUrl)
    
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value))
        }
      })
    }
    
    return url.toString()
  }
  
  // 序列化请求数据
  static serializeData(data: any, contentType: string): any {
    if (contentType.includes('application/json')) {
      return JSON.stringify(data)
    }
    
    if (contentType.includes('multipart/form-data')) {
      const formData = new FormData()
      
      Object.entries(data).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (value instanceof File || value instanceof Blob) {
            formData.append(key, value)
          } else {
            formData.append(key, String(value))
          }
        }
      })
      
      return formData
    }
    
    if (contentType.includes('application/x-www-form-urlencoded')) {
      const searchParams = new URLSearchParams()
      
      Object.entries(data).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value))
        }
      })
      
      return searchParams
    }
    
    return data
  }
  
  // 解析响应数据
  static async parseResponse(response: Response): Promise<any> {
    const contentType = response.headers.get('content-type') || ''
    
    if (contentType.includes('application/json')) {
      return response.json()
    }
    
    if (contentType.includes('text/')) {
      return response.text()
    }
    
    if (contentType.includes('image/') || contentType.includes('audio/')) {
      return response.blob()
    }
    
    return response.arrayBuffer()
  }
}