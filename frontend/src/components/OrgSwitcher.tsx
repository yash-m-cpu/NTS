import { useAuthStore } from '../state/authStore';

export default function OrgSwitcher() {
  const { user, activeOrgId, setActiveOrgId } = useAuthStore();

  if (!user || !user.organizations || user.organizations.length === 0) {
    return null;
  }

  return (
    <select 
      value={activeOrgId || ''} 
      onChange={(e) => setActiveOrgId(e.target.value)}
      className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
    >
      {user.organizations.map((org) => (
        <option key={org.id} value={org.id}>
          {org.name}
        </option>
      ))}
    </select>
  );
}
