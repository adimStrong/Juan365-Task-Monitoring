import { Link } from 'react-router-dom';
import { ROUTES } from '../constants/routes';

/**
 * 404 Not Found page component
 * Displayed when user navigates to a route that doesn't exist
 */
const NotFound = () => {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
      <div className="max-w-lg w-full text-center">
        <div className="mb-8">
          <h1 className="text-9xl font-bold text-gray-300">404</h1>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Page Not Found
        </h2>
        <p className="text-gray-600 mb-8">
          Sorry, the page you're looking for doesn't exist or has been moved.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            to={ROUTES.HOME}
            className="px-6 py-3 min-h-[44px] bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium inline-flex items-center justify-center"
          >
            Go to Dashboard
          </Link>
          <Link
            to={ROUTES.TICKETS}
            className="px-6 py-3 min-h-[44px] bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium inline-flex items-center justify-center"
          >
            View Tickets
          </Link>
        </div>
      </div>
    </div>
  );
};

export default NotFound;
