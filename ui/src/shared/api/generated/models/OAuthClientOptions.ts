/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * How to talk to one vendor's authorize and token endpoints.
 */
export type OAuthClientOptions = {
    /**
     * Extra authorize-URL parameters for this vendor; they win over the provider's authorize_extra_params and may not set protocol parameters.
     */
    authorize_params?: Record<string, string>;
    /**
     * Non-secret token-response fields to keep as server variables: dotted response path to server variable name (at most 20).
     */
    keep_token_fields?: Record<string, string>;
    /**
     * Send an RFC 7636 S256 PKCE challenge.
     */
    pkce?: boolean;
    /**
     * The callback registered with the vendor, when it is not this deployment's own (for example an app that relays the callback here).
     */
    redirect_uri?: (string | null);
    /**
     * RFC 6749 §2.3.1 client authentication: the secret in the body, or HTTP Basic.
     */
    token_auth_method?: OAuthClientOptions.token_auth_method;
    /**
     * Encoding of the token request body.
     */
    token_request_encoding?: OAuthClientOptions.token_request_encoding;
};
export namespace OAuthClientOptions {
    /**
     * RFC 6749 §2.3.1 client authentication: the secret in the body, or HTTP Basic.
     */
    export enum token_auth_method {
        CLIENT_SECRET_POST = 'client_secret_post',
        CLIENT_SECRET_BASIC = 'client_secret_basic',
    }
    /**
     * Encoding of the token request body.
     */
    export enum token_request_encoding {
        FORM = 'form',
        JSON = 'json',
    }
}

