/**
 * Deliberate failure injection — admin-only, internal listener only.
 *
 * <p>Three triggers, each mapped to a specific row in the Ops Sentinel risk register so the
 * demo proves something rather than merely working:
 *
 * <ol>
 *   <li><b>Bad deploy → elevated 5xx</b> — a real ECS deployment of a broken task-definition
 *       revision. Not scripted; an actual bad rollout. Exercises blast radius / rollback-required.
 *   <li><b>Memory leak → OOM restarts</b> — {@code POST /admin/chaos/leak} appends to a static
 *       list until the container genuinely OOMs. Exercises the cost ceiling.
 *   <li><b>Injected log line</b> — {@code POST /admin/chaos/log-injection} logs a crafted ERROR
 *       designed to read as an instruction. Exercises prompt-injection defense.
 * </ol>
 *
 * <p><b>Security requirement, not a nicety:</b> these endpoints are themselves a risk if reachable
 * by anyone but the operator. They require an admin API key header and must be bound to the
 * internal listener — reachable via VPN or SSM port-forward, never the public ALB route.
 * Applying the same risk discipline to the sandbox app that the project applies to the AI watching
 * it is part of the story.
 */
package com.opssentinel.orders.chaos;
