/**
 * Dojo Client - TypeScript client for Ninja Operations
 *
 * Use this in BeeBill to talk to the Dojo server running on the Linux box.
 *
 * Usage:
 *   const dojo = new DojoClient("http://192.168.86.20:9565")
 *   const result = await dojo.dispatch("parser", "parse_invoice", { text: "3 hours at $150" })
 */

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface ScrollMeta {
  schema: string
  version: number
  hash: string
  time: number
  prev?: string[]
  op?: string
  influence?: number
}

export interface Scroll<T = unknown> {
  key: string
  data: T
  meta: ScrollMeta
}

export interface JutsuResult {
  response: string
  jutsu: string
  model: string
  elapsed: number
}

export interface NinjaInfo {
  name: string
  model: string
  chakra_affinity: string
  jutsu: string[]
  jutsu_count: number
}

export interface JutsuInfo {
  name: string
  description: string
  chakra_type: string
}

export interface DojoStatus {
  status: string
  hokage: string
  ninjas: string[]
  missions_completed: number
}

export interface CombinationStep {
  ninja: string
  jutsu: string
  kwargs?: Record<string, unknown>
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CLIENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export class DojoClient {
  private baseUrl: string

  constructor(baseUrl: string = "http://localhost:9565") {
    this.baseUrl = baseUrl.replace(/\/$/, "")
  }

  private async fetch<T>(
    path: string,
    options?: RequestInit
  ): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: "Unknown error" }))
      throw new Error(error.error || `HTTP ${response.status}`)
    }

    return response.json()
  }

  // ── Status ────────────────────────────────────────────────

  async status(): Promise<DojoStatus> {
    return this.fetch<DojoStatus>("/status")
  }

  async ninjas(): Promise<Record<string, NinjaInfo>> {
    return this.fetch<Record<string, NinjaInfo>>("/ninjas")
  }

  async jutsu(): Promise<Record<string, JutsuInfo>> {
    return this.fetch<Record<string, JutsuInfo>>("/jutsu")
  }

  async contracts(): Promise<string[]> {
    return this.fetch<string[]>("/contracts")
  }

  // ── Operations ────────────────────────────────────────────

  /**
   * Dispatch a ninja to perform a jutsu.
   *
   * @example
   * const result = await dojo.dispatch("parser", "parse_invoice", { text: "3 hours at $150" })
   * console.log(result.data.response) // JSON string with parsed invoice
   */
  async dispatch(
    ninja: string,
    jutsu: string,
    kwargs: Record<string, unknown> = {}
  ): Promise<Scroll<JutsuResult>> {
    return this.fetch<Scroll<JutsuResult>>("/dispatch", {
      method: "POST",
      body: JSON.stringify({ ninja, jutsu, kwargs }),
    })
  }

  /**
   * Execute shadow clone army - parallel jutsu execution.
   *
   * @example
   * const results = await dojo.shadowCloneArmy("parser", "parse_invoice", [
   *   { text: "3 hours at $150" },
   *   { text: "5 pages at $100" },
   * ])
   */
  async shadowCloneArmy(
    ninja: string,
    jutsu: string,
    tasks: Record<string, unknown>[]
  ): Promise<Scroll<JutsuResult>[]> {
    return this.fetch<Scroll<JutsuResult>[]>("/shadow-clone-army", {
      method: "POST",
      body: JSON.stringify({ ninja, jutsu, tasks }),
    })
  }

  /**
   * Execute combination jutsu - chain multiple steps.
   *
   * @example
   * const result = await dojo.combination([
   *   { ninja: "parser", jutsu: "parse_invoice", kwargs: { text: "..." } },
   *   { ninja: "writer", jutsu: "summarize", kwargs: { text: "{previous}" } },
   * ])
   */
  async combination(steps: CombinationStep[]): Promise<Scroll> {
    return this.fetch<Scroll>("/combination", {
      method: "POST",
      body: JSON.stringify({ steps }),
    })
  }

  /**
   * Summon a new ninja using a contract.
   *
   * @example
   * await dojo.summon("parser") // Summons a new parser ninja
   */
  async summon(contract: string): Promise<{ summoned: string; jutsu: string[] }> {
    return this.fetch<{ summoned: string; jutsu: string[] }>("/summon", {
      method: "POST",
      body: JSON.stringify({ contract }),
    })
  }

  /**
   * Execute raw prompt on a ninja.
   *
   * @example
   * const result = await dojo.raw("parser", "What is 2+2?")
   */
  async raw(ninja: string, prompt: string): Promise<Scroll<JutsuResult>> {
    return this.fetch<Scroll<JutsuResult>>("/raw", {
      method: "POST",
      body: JSON.stringify({ ninja, prompt }),
    })
  }

  // ── Convenience Methods ───────────────────────────────────

  /**
   * Parse an invoice description.
   *
   * @example
   * const invoice = await dojo.parseInvoice("3 hours consulting at $150/hr")
   * // { client: "...", lineItems: [...] }
   */
  async parseInvoice(text: string): Promise<{
    client: string
    lineItems: Array<{ description: string; quantity: number; rate: number }>
  } | null> {
    const result = await this.dispatch("parser", "parse_invoice", { text })
    const response = result.data.response

    try {
      // Extract JSON from response
      const match = response.match(/\{[\s\S]*\}/)
      if (match) {
        return JSON.parse(match[0])
      }
    } catch {
      // Parse failed
    }

    return null
  }

  /**
   * Parse multiple invoices in parallel.
   */
  async parseInvoices(texts: string[]): Promise<Array<{
    client: string
    lineItems: Array<{ description: string; quantity: number; rate: number }>
  } | null>> {
    const tasks = texts.map(text => ({ text }))
    const results = await this.shadowCloneArmy("parser", "parse_invoice", tasks)

    return results.map(result => {
      try {
        const match = result.data.response.match(/\{[\s\S]*\}/)
        if (match) {
          return JSON.parse(match[0])
        }
      } catch {
        // Parse failed
      }
      return null
    })
  }

  /**
   * Analyze a problem dialectically.
   */
  async analyzeDialectically(problem: string): Promise<string> {
    const result = await this.dispatch("analyst", "dialectic", { problem })
    return result.data.response
  }

  /**
   * Summarize text.
   */
  async summarize(text: string): Promise<string> {
    const result = await this.dispatch("writer", "summarize", { text })
    return result.data.response
  }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// REACT HOOK (for BeeBill)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// Uncomment for React usage:
/*
import { useState, useCallback, useMemo } from 'react'

export function useDojo(baseUrl: string = "http://localhost:9565") {
  const client = useMemo(() => new DojoClient(baseUrl), [baseUrl])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const dispatch = useCallback(async (
    ninja: string,
    jutsu: string,
    kwargs: Record<string, unknown> = {}
  ) => {
    setLoading(true)
    setError(null)
    try {
      return await client.dispatch(ninja, jutsu, kwargs)
    } catch (e) {
      setError(e as Error)
      throw e
    } finally {
      setLoading(false)
    }
  }, [client])

  const parseInvoice = useCallback(async (text: string) => {
    setLoading(true)
    setError(null)
    try {
      return await client.parseInvoice(text)
    } catch (e) {
      setError(e as Error)
      throw e
    } finally {
      setLoading(false)
    }
  }, [client])

  return {
    client,
    loading,
    error,
    dispatch,
    parseInvoice,
    summarize: client.summarize.bind(client),
    analyzeDialectically: client.analyzeDialectically.bind(client),
  }
}
*/

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// EXAMPLE USAGE
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/*
// In BeeBill:
import { DojoClient } from '@/lib/dojo/client'

const dojo = new DojoClient("http://192.168.86.20:9565")

// Parse natural language invoice
const invoice = await dojo.parseInvoice("3 hours consulting for Acme at $150/hr")
// → { client: "Acme", lineItems: [{ description: "consulting", quantity: 3, rate: 150 }] }

// Batch process
const invoices = await dojo.parseInvoices([
  "5 hours design at $100",
  "Monthly retainer $2000",
])

// Get dialectic analysis
const analysis = await dojo.analyzeDialectically(
  "Should we add more features or simplify?"
)
*/

export default DojoClient
