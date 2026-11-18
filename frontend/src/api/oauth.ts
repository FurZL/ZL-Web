import { request } from './client'
import type { OauthProviderInfo, OauthResolveResult } from '@/types'

export function getOauthProviders() {
  return request<{ providers: OauthProviderInfo[]; frontend_base_url: string }>({
    method: 'GET',
    url: '/auth/oauth/providers',
  })
}

export function startQqLogin(verificationToken: string, returnTo?: string) {
  return request<{ authorize_url: string }>({
    method: 'POST',
    url: '/auth/oauth/qq/start',
    data: {
      verification_token: verificationToken || undefined,
      return_to: returnTo || undefined,
    },
  })
}

export function startQqBind(verificationToken: string, returnTo?: string) {
  return request<{ authorize_url: string }>({
    method: 'POST',
    url: '/auth/oauth/qq/bind-start',
    data: {
      verification_token: verificationToken || undefined,
      return_to: returnTo || undefined,
    },
  })
}

export function exchangeQqCallback(code: string, state: string) {
  return request<OauthResolveResult>({
    method: 'GET',
    url: '/auth/oauth/qq/callback',
    params: { code, state },
  })
}

export function bindQqWithAccount(
  oauthToken: string,
  account: string,
  password: string,
  verificationToken: string,
) {
  return request<OauthResolveResult>({
    method: 'POST',
    url: '/auth/oauth/qq/bind',
    data: {
      oauth_token: oauthToken,
      account,
      password,
      verification_token: verificationToken,
    },
  })
}

export function getMyThirdPartyBindings() {
  return request<{ items: import('@/types').ThirdPartyBinding[] }>({
    method: 'GET',
    url: '/profile/me/third-party',
  })
}

export function deleteMyThirdPartyBinding(provider: string) {
  return request<{ message: string }>({
    method: 'DELETE',
    url: `/profile/me/third-party/${provider}`,
  })
}
