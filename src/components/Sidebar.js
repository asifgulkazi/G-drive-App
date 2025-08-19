import React, { useState } from 'react';
import '../../styles/Sidebar.css';
import SidebarItem from './SidebarItem';
import FileUpload from '../FileUpload'; // Import the new component

// Material-UI Icons
import InsertDriveFileIcon from '@material-ui/icons/InsertDriveFile';
import ImportantDevicesIcon from '@material-ui/icons/ImportantDevices';
import PeopleAltIcon from '@material-ui/icons/PeopleAlt';
import QueryBuilderIcon from '@material-ui/icons/QueryBuilder';
import StarBorderIcon from '@material-ui/icons/StarBorder';
import DeleteOutlineIcon from '@material-ui/icons/DeleteOutline';
import StorageIcon from '@material-ui/icons/Storage';
import CloudUploadIcon from '@material-ui/icons/CloudUpload'; // Icon for the new upload button

const Sidebar = () => {
    // State for managing the visibility of the upload modal
    const [openUpload, setOpenUpload] = useState(false);

    // Function to open the modal
    const handleOpenUpload = () => {
        setOpenUpload(true);
    };

    // Function to close the modal
    const handleCloseUpload = () => {
        setOpenUpload(false);
    };

    return (
        <div className='sidebar'>
            {/* The FileUpload modal component. It remains in the DOM but is only visible when 'openUpload' is true. */}
            <FileUpload open={openUpload} handleClose={handleCloseUpload} />

            <div className="sidebar__btn">
                <button>New</button>
            </div>

            <div className="sidebar__options">
                <SidebarItem arrow icon={(<InsertDriveFileIcon />)} label={'My Drive'} />
                <SidebarItem arrow icon={(<ImportantDevicesIcon />)} label={'Computers'} />
                <SidebarItem icon={(<PeopleAltIcon />)} label={'Shared with me'} />
                <SidebarItem icon={(<QueryBuilderIcon />)} label={'Recent'} />
                <SidebarItem icon={(<StarBorderIcon />)} label={'Starred'} />
                <SidebarItem icon={(<DeleteOutlineIcon />)} label={'Bin'} />
                
                <hr/>
                
                {/* New Sidebar Item to trigger the upload modal */}
                <div onClick={handleOpenUpload}>
                    <SidebarItem icon={(<CloudUploadIcon />)} label={'File / Folder Upload'} />
                </div>
            </div>

            <div className="sidebar__footer">
                <div className="sidebar__footer--left">
                    <StorageIcon />
                    <span>0 GB of 15 GB used</span>
                </div>
                <button>Buy storage</button>
            </div>
        </div>
    )
}

export default Sidebar;
