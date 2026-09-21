const engines: Partial<Record<EngineName, RecognitionEngine>> = {}

/** Active Recognition Engine, selected by env ENGINE=vector|stub. */
export function getEngine(): RecognitionEngine {
  const name = appConfig.engine
  return (engines[name] ??= name === 'stub' ? new StubEngine() : new VectorEngine())
}
