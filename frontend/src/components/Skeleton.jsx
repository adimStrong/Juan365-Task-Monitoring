// Reusable skeleton components for loading states

export const SkeletonBox = ({ className = '' }) => (
  <div className={`animate-pulse bg-gray-200 rounded ${className}`} />
);

export const SkeletonText = ({ lines = 1, className = '' }) => (
  <div className={`space-y-2 ${className}`}>
    {[...Array(lines)].map((_, i) => (
      <div
        key={i}
        className="animate-pulse bg-gray-200 rounded h-4"
        style={{ width: i === lines - 1 && lines > 1 ? '60%' : '100%' }}
      />
    ))}
  </div>
);

export const SkeletonCard = ({ className = '' }) => (
  <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
    <div className="animate-pulse space-y-4">
      <div className="flex items-center justify-between">
        <SkeletonBox className="h-4 w-24" />
        <SkeletonBox className="h-10 w-10 rounded-full" />
      </div>
      <SkeletonBox className="h-8 w-16" />
      <SkeletonBox className="h-3 w-20" />
    </div>
  </div>
);

export const SkeletonTable = ({ rows = 5, cols = 6 }) => (
  <div className="bg-white shadow rounded-lg overflow-hidden">
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {[...Array(cols)].map((_, i) => (
              <th key={i} className="px-6 py-3">
                <SkeletonBox className="h-4 w-20" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {[...Array(rows)].map((_, rowIndex) => (
            <tr key={rowIndex}>
              {[...Array(cols)].map((_, colIndex) => (
                <td key={colIndex} className="px-6 py-4">
                  <SkeletonBox className="h-4 w-full" />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

export const SkeletonTicketDetail = () => (
  <div className="space-y-6">
    {/* Header */}
    <div className="flex items-center justify-between">
      <div className="space-y-2">
        <SkeletonBox className="h-4 w-24" />
        <SkeletonBox className="h-8 w-64" />
      </div>
      <div className="flex space-x-2">
        <SkeletonBox className="h-8 w-20 rounded-full" />
        <SkeletonBox className="h-8 w-16 rounded-full" />
      </div>
    </div>

    {/* Actions */}
    <div className="bg-white shadow rounded-lg p-4">
      <SkeletonBox className="h-4 w-16 mb-3" />
      <div className="flex gap-2">
        <SkeletonBox className="h-10 w-24 rounded-md" />
        <SkeletonBox className="h-10 w-24 rounded-md" />
      </div>
    </div>

    {/* Content Grid */}
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        {/* Description */}
        <div className="bg-white shadow rounded-lg p-6">
          <SkeletonBox className="h-6 w-32 mb-4" />
          <SkeletonText lines={4} />
        </div>
        {/* Comments */}
        <div className="bg-white shadow rounded-lg p-6">
          <SkeletonBox className="h-6 w-32 mb-4" />
          <div className="space-y-4">
            {[1, 2].map((i) => (
              <div key={i} className="border-b pb-4">
                <div className="flex items-center justify-between mb-2">
                  <SkeletonBox className="h-4 w-24" />
                  <SkeletonBox className="h-3 w-32" />
                </div>
                <SkeletonText lines={2} />
              </div>
            ))}
          </div>
        </div>
      </div>
      {/* Sidebar */}
      <div className="space-y-6">
        <div className="bg-white shadow rounded-lg p-6">
          <SkeletonBox className="h-6 w-20 mb-4" />
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i}>
                <SkeletonBox className="h-3 w-16 mb-1" />
                <SkeletonBox className="h-4 w-32" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  </div>
);

export const DashboardSkeleton = () => (
  <div className="space-y-6">
    {/* Header */}
    <div className="flex items-center justify-between">
      <SkeletonBox className="h-8 w-48" />
      <SkeletonBox className="h-10 w-32 rounded-md" />
    </div>

    {/* Stats Cards */}
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {[1, 2, 3, 4].map((i) => (
        <SkeletonCard key={i} />
      ))}
    </div>

    {/* Recent Tickets */}
    <div className="bg-white shadow rounded-lg p-6">
      <SkeletonBox className="h-6 w-40 mb-4" />
      <div className="space-y-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex items-center justify-between py-2 border-b">
            <div className="flex-1">
              <SkeletonBox className="h-4 w-3/4 mb-2" />
              <SkeletonBox className="h-3 w-1/2" />
            </div>
            <SkeletonBox className="h-6 w-20 rounded-full" />
          </div>
        ))}
      </div>
    </div>
  </div>
);

export const TicketListSkeleton = () => (
  <div className="space-y-6">
    {/* Header */}
    <div className="flex items-center justify-between">
      <SkeletonBox className="h-8 w-32" />
      <SkeletonBox className="h-10 w-32 rounded-md" />
    </div>

    {/* Search & Filters */}
    <div className="bg-white shadow rounded-lg p-4">
      <div className="flex gap-4">
        <SkeletonBox className="h-10 flex-1 rounded-md" />
        <SkeletonBox className="h-10 w-24 rounded-md" />
        <SkeletonBox className="h-10 w-24 rounded-md" />
      </div>
    </div>

    {/* Results count */}
    <SkeletonBox className="h-4 w-32" />

    {/* Table */}
    <SkeletonTable rows={8} cols={6} />
  </div>
);
