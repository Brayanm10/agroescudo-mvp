export class LatestRequest {
  private generation = 0;

  begin() {
    this.generation += 1;
    return this.generation;
  }

  isCurrent(generation: number) {
    return generation === this.generation;
  }

  cancelAll() {
    this.generation += 1;
  }
}
