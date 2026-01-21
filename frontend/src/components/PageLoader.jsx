/**
 * Loading spinner component for lazy loaded pages and route protection
 */
const PageLoader = () => (
  <div className="min-h-screen flex flex-col items-center justify-center bg-gray-100">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
    <p className="mt-4 text-gray-600">Loading, please wait...</p>
  </div>
);

export default PageLoader;
