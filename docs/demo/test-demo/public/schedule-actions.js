(function (root) {
  async function performScheduleAction(operation, onSuccess, onError) {
    try {
      await operation();
      await onSuccess();
      return true;
    } catch (error) {
      onError(error);
      return false;
    }
  }

  root.performScheduleAction = performScheduleAction;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { performScheduleAction };
  }
})(typeof window !== "undefined" ? window : globalThis);
