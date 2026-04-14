import axios from 'axios';

export interface UndoResponse {
  success: boolean;
  action_reverted?: string;
  message: string;
}

class UndoRedoService {
  private baseUrl: string = '/api/graph';

  /**
   * Hoàn tác hành động gần nhất của người dùng trên đồ thị của document.
   */
  async undo(documentId: string): Promise<UndoResponse> {
    try {
      const response = await axios.post(`${this.baseUrl}/${documentId}/undo`);
      return response.data;
    } catch (error) {
      console.error('Failed to undo graph action:', error);
      return { success: false, message: 'Lỗi kết nối khi hoàn tác' };
    }
  }

  /**
   * Lưu một phiên bản snapshot mới cho đồ thị.
   */
  async createSnapshot(documentId: string, name: string, description?: string): Promise<any> {
    try {
      const response = await axios.post(`${this.baseUrl}/${documentId}/versions`, {
        version_name: name,
        description: description,
        is_auto_save: false
      });
      return response.data;
    } catch (error) {
      console.error('Failed to create graph snapshot:', error);
      throw error;
    }
  }

  /**
   * Lấy danh sách các phiên bản snapshot.
   */
  async getVersions(documentId: string): Promise<any[]> {
    try {
      const response = await axios.get(`${this.baseUrl}/${documentId}/versions`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch graph versions:', error);
      return [];
    }
  }

  /**
   * Khôi phục đồ thị về một phiên bản snapshot.
   */
  async restoreVersion(documentId: string, versionId: string): Promise<boolean> {
    try {
      await axios.post(`${this.baseUrl}/${documentId}/restore/${versionId}`);
      return true;
    } catch (error) {
      console.error('Failed to restore graph version:', error);
      return false;
    }
  }
}

export const undoRedoService = new UndoRedoService();
