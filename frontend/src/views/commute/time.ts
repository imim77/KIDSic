export const time = (value: string) => new Intl.DateTimeFormat('hr-HR', {
  timeZone: 'Europe/Zagreb', hour: '2-digit', minute: '2-digit',
}).format(new Date(value))

