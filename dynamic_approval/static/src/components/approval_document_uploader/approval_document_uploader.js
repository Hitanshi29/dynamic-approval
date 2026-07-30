/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef } from "@odoo/owl";

export class ApprovalDocumentUploader extends Component {
    static template = "approval_document_uploader.ApprovalDocumentUploader";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.fileInput = useRef("fileInput");
    }

    /**
     * Triggered when the attachment button is clicked.
     * Opens the native file picker.
     */
    onUploadClick() {
        this.fileInput.el.click();
    }

    /**
     * Triggered when the user selects one or more files.
     */
    async onFileChange(ev) {
        const files = ev.target.files;
        if (!files.length) {
            return;
        }
        for (const file of files) {
            await this.uploadFile(file);
        }
        // reset so selecting the same file again still fires change
        ev.target.value = "";
    }

    async uploadFile(file) {
        try {
            const base64Data = await this._getFileAsBase64(file);
            const resModel = this.props.record.resModel;
            const resId = this.props.record.resId;

            await this.orm.create("ir.attachment", [{
                name: file.name,
                datas: base64Data,
                res_model: resModel,
                res_id: resId,
                mimetype: file.type,
            }]);

            this.notification.add(
                `"${file.name}" uploaded successfully.`,
                { type: "success" }
            );

            // Reload so the paperclip/attachment count refreshes.
            await this.props.record.load();
        } catch (error) {
            this.notification.add(
                `Failed to upload "${file.name}".`,
                { type: "danger" }
            );
            console.error(error);
        }
    }

    // async uploadFile(file) {
    //     try {
    //         const base64Data = await this._getFileAsBase64(file);
    //         const resModel = this.props.record.resModel;
    //         const resId = this.props.record.resId;

    //         await this.orm.create("ir.attachment", [{
    //             name: file.name,
    //             datas: base64Data,
    //             res_model: resModel,
    //             res_id: resId,
    //             mimetype: file.type,
    //         }]);

    //         this.notification.add(
    //             `"${file.name}" uploaded successfully.`,
    //             { type: "success" }
    //         );

    //         // reload the record so any attachment count / list refreshes
    //         await this.props.record.load();
    //     } catch (error) {
    //         this.notification.add(
    //             `Failed to upload "${file.name}".`,
    //             { type: "danger" }
    //         );
    //         console.error(error);
    //     }
    // }

    _getFileAsBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result.split(",")[1]);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }
}

// Register as a generic view widget so it can be used as:
// <widget name="approval_document_uploader"/>
registry.category("view_widgets").add("approval_document_uploader", {
    component: ApprovalDocumentUploader,
});