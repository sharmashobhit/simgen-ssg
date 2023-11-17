# import asyncio
# from unittest.mock import MagicMock

# from simgen_ssg.__main__ import main


# async def test_main():
#     # Mock the setup_qdrant function
#     main.setup_qdrant = MagicMock()

#     # Mock the serve and file_watcher coroutines
#     main.serve = MagicMock()
#     main.file_watcher = MagicMock()

#     # Call the main function
#     await main.main()

#     # Assert that the setup_qdrant function was called
#     main.setup_qdrant.assert_called_once()

#     # Assert that the serve and file_watcher coroutines were called with the correct arguments
#     main.serve.assert_called_once_with(main.app, main.Config())
#     main.file_watcher.assert_called_once()

#     # Assert that the serve and file_watcher coroutines were called concurrently
#     asyncio.gather.assert_called_once_with(main.serve(), main.file_watcher())
